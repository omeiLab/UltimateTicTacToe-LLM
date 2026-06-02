import sys
from minimax_model.agent import MinimaxAgent

class MinimaxAdapter:
    def __init__(self, model_player="O", time_limit=3.0):
        """
        model_player: "X" or "O" 
        """
        self.model_player = model_player
        self.time_limit = time_limit
        self.agent = None
        
    def reset_agent(self, starting_player_id: int = 1):
        """
        
        """
        start_char = "X" if starting_player_id == 1 else "O"
        
        self.agent = MinimaxAgent(
            model_player=self.model_player,
            starting_player=start_char,
            debug=False,
            max_depth=80,
            time_limit_sec=self.time_limit
        )

    def get_move(self, engine, legal_moves: list) -> dict:
        """
        
        """
        if self.agent is None:
            total_pieces = sum(1 for b in range(9) for r in range(3) for c in range(3) if engine.board[b][r][c] != 0)
            current_player_id = 1 if total_pieces % 2 == 0 else 2
            self.reset_agent(starting_player_id=current_player_id)

        opponent_move = None
        if engine.history:
            last_b, last_r, last_c, last_pid = engine.history[-1]
            opp_char = "O" if self.model_player == "X" else "X"
            last_p_char = "X" if last_pid == 1 else "O"
            
            if last_p_char == opp_char:
                opponent_move = {
                    "board": last_b,
                    "row": last_r,
                    "col": last_c
                }

        if opponent_move:
            result = self.agent.step(opponent_move)
        else:
            result = self.agent.step()

        if result["status"] in ["ok", "game_over"] and result["move"] is not None:
            m = result["move"]
            thinking_time = result.get("stats", {}).get("thinking_time_sec", 0.0)
            
            return {
                "box": m["board"],
                "row": m["row"],
                "col": m["col"],
                "reason": f"[Minimax]. Thinking time: {thinking_time:.3f}"
            }
        else:
            fallback = legal_moves[0]
            err_msg = result.get("error", {}).get("message", "Unknown Minimax Error")
            return {
                "box": fallback[0],
                "row": fallback[1],
                "col": fallback[2],
                "reason": f"[Minimax Fallback] Error: ({err_msg})"
            }