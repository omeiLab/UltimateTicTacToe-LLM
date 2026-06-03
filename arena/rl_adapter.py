# src/arena/rl_adapter.py
import os
import torch
import numpy as np
from RL.RL import UTTTNet  
from RL.mcts import MCTS   
from RL.uttt_env import UltimateTicTacToeEnv 

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class RLAdapter:
    def __init__(self, model_id=200, num_simulations=200, model_player="O"):
        """
        model_player: X (ID=1), "O" (ID=2)
        """
        self.model_player = model_player
        self.num_simulations = num_simulations
        self.model_path = f"../RL/checkpoints/uttt_model_iter_{model_id}.pth"
        self.model = UTTTNet(num_res_blocks=3, num_channels=64).to(DEVICE)
        
        if os.path.exists(self.model_path):
            state_dict = torch.load(self.model_path, map_location=DEVICE, weights_only=True)
            self.model.load_state_dict(state_dict)
            print(f"[RL Adapter] AlphaZero Neural Network loaded from {self.model_path} ({DEVICE})")
        else:
            print(f"[RL Adapter] Checkpoint {self.model_path} not found! Using random initialized weights.")
        
        self.model.eval()
        self.mcts = MCTS(self.model, DEVICE, c_puct=1.4, num_simulations=num_simulations)
        self.env = None

    def reset_agent(self, starting_player_id: int = 1):
        self.env = UltimateTicTacToeEnv()
        self.env.reset()
        print(f"[RL Adapter] Stateful virtual RL environment refreshed.")

    def _to_rl_action(self, b: int, r: int, c: int) -> int:
        micro_idx = b
        cell_idx = r * 3 + c
        return micro_idx * 9 + cell_idx

    def _from_rl_action(self, action_1d: int) -> tuple:
        b = action_1d // 9
        cell_idx = action_1d % 9
        r = cell_idx // 3
        c = cell_idx % 3
        return b, r, c

    def get_move(self, engine, legal_moves: list) -> dict:
        if self.env is None:
            self.reset_agent()

        try:
            total_pieces = sum(1 for b in range(9) for r in range(3) for c in range(3) if engine.board[b][r][c] != 0)
            if total_pieces > 0 and hasattr(engine, 'history') and engine.history:
                last_opp_b, last_opp_r, last_opp_c, last_opp_pid = engine.history[-1]
                opp_action_1d = self._to_rl_action(last_opp_b, last_opp_r, last_opp_c)
                if self.env.get_legal_actions()[opp_action_1d] == 1:
                    self.env.step(opp_action_1d)

            self.model.eval()
            with torch.no_grad():
                action_probs = self.mcts.get_action_prob(self.env, temp=0, add_noise=False)

            best_action_1d = int(np.argmax(action_probs))
            self.env.step(best_action_1d)
            b, r, c = self._from_rl_action(best_action_1d)
            
            return {
                "box": b,
                "row": r,
                "col": c,
                "reason": f"[AlphaZero RL] {best_action_1d}"
            }

        except Exception as e:
            fallback = legal_moves[0]
            return {
                "box": fallback[0], "row": fallback[1], "col": fallback[2],
                "reason": f"[RL Adapter Exception] ({str(e)})"
            }