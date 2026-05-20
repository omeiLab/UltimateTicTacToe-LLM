import copy
from llm_agent import BaseAgent

class MediumAgent(BaseAgent):
    """
    Medium: Depth-2 Minimax Bounded Adversarial Lookahead
    """

    def build_prompt(self, engine_state_str: str, legal_moves: list) -> str:
        """
        Let Qwen propose 3 candidate moves with reasons, 
        but we will do the final selection in Python with a depth-2 minimax lookahead 
        to simulate the opponent's best response and evaluate the net gain of each candidate move.
        """
        return f"""
You are an expert Ultimate Tic-Tac-Toe strategist.
Current Board State:
{engine_state_str}

Valid Moves (box, row, col):
{legal_moves}

Propose exactly 3 DIFFERENT candidate moves from the Valid Moves, ordered from highest recommendation to lowest.
Output MUST be in valid JSON format ONLY.
Structure:
{{
  "candidates": [
    {{"box": int, "row": int, "col": int, "reason": "string"}},
    {{"box": int, "row": int, "col": int, "reason": "string"}},
    {{"box": int, "row": int, "col": int, "reason": "string"}}
  ]
}}
Do not include any other text outside the JSON object.
"""

    def get_move(self, engine, legal_moves: list) -> dict:
        """
        1. Get 3 candidate moves from LLM with reasons.
        2. For each candidate, simulate that move on a virtual board.
        3. For each simulated board, calculate the opponent's best possible response and its damage.
        4. Score each candidate move based on its own gain minus the opponent's best response damage.
        """
        state_str = engine.to_llm_string()
        prompt = self.build_prompt(state_str, legal_moves)
        result = self._call_llm_and_parse_json(prompt)
        candidates = result.get("candidates", [])

        # Take the top 3 candidates, but if JSON parsing failed or no candidates, fallback to the first 3 legal moves with a note
        if "error" in result or not candidates:
            candidates = [{"box": m[0], "row": m[1], "col": m[2], "reason": "Fallback"} for m in legal_moves[:3]]

        best_action = None
        best_score = -99999

        # Depth-2 Minimax
        for cand in candidates:
            try:
                b, r, c = int(cand["box"]), int(cand["row"]), int(cand["col"])
            except (KeyError, ValueError, TypeError):
                continue
                
            # Filter out any candidate that is not in legal moves (just in case)
            if (b, r, c) not in legal_moves:
                continue
                
            # Layer 1: Simulate AI's candidate move on a virtual board
            virtual_engine = copy.deepcopy(engine)
            virtual_engine.make_move(b, r, c, player=2)
            
            # Layer 2: Simulate opponent's best response (assuming opponent also plays optimally)
            human_legal_replies = virtual_engine.get_legal_moves()
            max_human_damage = 0
            
            for hb, hr, hc in human_legal_replies:
                damage = 0
                sim_sub_board = copy.deepcopy(virtual_engine.board[hb])
                sim_sub_board[hr][hc] = 1
                
                # Simple heuristic for opponent's damage: 
                # if this move wins them the sub-board it's a big threat (100 points).
                if virtual_engine.check_line_win(sim_sub_board) == 1:
                    damage += 100
                    
                if damage > max_human_damage:
                    max_human_damage = damage

            # Calculate AI's gain from the candidate move: 
            # if it wins a sub-board, it's a big gain (80 points).
            my_gain = 0
            sim_my_board = copy.deepcopy(engine.board[b])
            sim_my_board[r][c] = 2 # 模擬自己點下去
            if engine.check_line_win(sim_my_board) == 2:
                my_gain += 80

            # Final score for this candidate = AI's gain - Opponent's best damage
            total_score = my_gain - max_human_damage
            
            if total_score > best_score:
                best_score = total_score
                best_action = {
                    "box": b, "row": r, "col": c,
                    "reason": f"{cand.get('reason','')} (Medium Sim: Gain +{my_gain}, Expected Enemy Damage -{max_human_damage})"
                }

        # Final decision
        if best_action:
            return best_action
        else:
            # Fallback
            fallback = legal_moves[0]
            return {
                "box": fallback[0], "row": fallback[1], "col": fallback[2], 
                "reason": "[Medium Fallback] Checked all candidates, none selected."
            }