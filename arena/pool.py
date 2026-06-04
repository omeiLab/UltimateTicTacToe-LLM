from LLM.easy_agent import EasyAgent
from LLM.medium_agent import MediumAgent
from LLM.phi_evaluator import PhiEvaluator
from .minimax_adapter import MinimaxAdapter
from .mcts_adapter import MCTSAdapter
from .rl_adapter import RLAdapter
from arena.arena import ArenaAgent

class AgentPool:
    def __init__(self):
        self._pool = {}
        self.mcts_path = "../Monte_Carlo/cpp/mcts_balance.cpp"
        self.initialize_all_agents()

    def initialize_all_agents(self):
        print("[AgentPool] Initialize...")

        # LLM Easy
        self._pool["easy"] = EasyAgent(model_name="qwen2.5:7b")
        
        # LLM Medium
        evaluator = PhiEvaluator(model="phi4-mini")
        self._pool["medium"] = MediumAgent(model_name="qwen2.5:7b", phi_evaluator=evaluator)

        # Minimax
        self._pool["minimax_X"] = MinimaxAdapter(model_player="X", time_limit=3.0)
        self._pool["minimax_O"] = MinimaxAdapter(model_player="O", time_limit=3.0)

        # MCTS
        self._pool["mcts_X"] = MCTSAdapter(exe_name="mcts_x_bin", model_player="X")
        self._pool["mcts_O"] = MCTSAdapter(exe_name="mcts_o_bin", model_player="O")

        # RL
        self._pool["rl_X"] = RLAdapter(model_id=170, num_simulations=1000, model_player="X")
        self._pool["rl_O"] = RLAdapter(model_id=170, num_simulations=1000, model_player="O")
        
        print("[AgentPool] Initialization complete. Agents available:", list(self._pool.keys()))

    def _resolve_key(self, mode_name: str, player_id: int) -> str:
        clean_mode = mode_name.replace("qwen_", "")
        
        if clean_mode == "minimax":
            return "minimax_X" if player_id == 1 else "minimax_O"
        if clean_mode == "mcts":
            return "mcts_X" if player_id == 1 else "mcts_O"
        if clean_mode == "rl":
            return "rl_X" if player_id == 1 else "rl_O"
        
        return clean_mode
    
    def get_agent(self, mode_name: str, player_id: int = 2):
        target_key = self._resolve_key(mode_name, player_id)
        if target_key not in self._pool:
            raise ValueError(f"{mode_name} is not a valid agent type.")
        return self._pool[target_key]
    
    def get_arena_agent(self, mode_name: str, player_id: int):
        target_key = self._resolve_key(mode_name, player_id)

        if target_key not in self._pool:
            raise ValueError(f"{mode_name} is not a valid mode. Available modes: {list(self._pool.keys())}")

        raw_brain = self._pool[target_key]
        
        role_name = f"P{player_id}-{mode_name.upper()}"
        return ArenaAgent(agent_instance=raw_brain, name=role_name)

    def prepare_for_new_game(self):
        for key in ["minimax_X", "minimax_O", "mcts_X", "mcts_O", "rl_X", "rl_O"]:
            agent = self._pool.get(key)
            if agent and hasattr(agent, "reset_agent"):
                agent.reset_agent()

    def get_pool_list(self):
        return list(self._pool.keys())