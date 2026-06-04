import copy
from .llm_agent import BaseAgent
from .tactical_engine import simulate_best_reply, fallback_move, tactical_score

PHI_EVAL_WEIGHT = 0.4
TACTICAL_WEIGHT = 0.6
OPPONENT_THREAT_WEIGHT = 1.0

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

Propose exactly 5 DIFFERENT candidate moves from the Valid Moves, ordered from highest recommendation to lowest.
Output MUST be in valid JSON format ONLY.
Structure:
{{
  "candidates": [
    {{"box": int, "row": int, "col": int, "reason": "string"}},
    {{"box": int, "row": int, "col": int, "reason": "string"}},
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

        # fallback if LLM failed
        if "error" in result or not candidates:
            return fallback_move(legal_moves)
        
        # check who is P1 and P2
        total_pieces = sum(1 for b in range(9) for r in range(3) for c in range(3) if engine.board[b][r][c] != 0)
        ai_player = 1 if total_pieces % 2 == 0 else 2
        opp_player = 2 if ai_player == 1 else 1

        best_action = None
        best_score = -99999

        for cand in candidates:
            try:
                b = int(cand["box"])
                r = int(cand["row"])
                c = int(cand["col"])
            except (KeyError, ValueError, TypeError):
                continue

            # skip hallucinated illegal moves
            if (b, r, c) not in legal_moves:
                continue

            # -------------------------------------------------
            # simulate my move
            # -------------------------------------------------
            virtual_engine = copy.deepcopy(engine)
            virtual_engine.make_move(b, r, c, player=ai_player)

            # -------------------------------------------------
            # deterministic opponent simulation
            # -------------------------------------------------
            opponent_move, opponent_damage = simulate_best_reply(
                virtual_engine,
                opponent_player=opp_player
            )

            # normalize
            opponent_damage /= 150.0

            # -------------------------------------------------
            # tactical self gain
            # (temporary heuristic before Phi evaluator)
            # -------------------------------------------------
            phi_score = self.phi.evaluate(virtual_engine, ai_player) if self.phi else 0
            determinstic_score = tactical_score(virtual_engine, b, r, c, player=ai_player)

            # normalize & clipping
            phi_score /= 100.0
            phi_score = max(-1.0, min(1.0, phi_score))
            determinstic_score /= 150.0

            # calculate my gain with weighted sum
            my_gain = phi_score * PHI_EVAL_WEIGHT + determinstic_score * TACTICAL_WEIGHT

            # -------------------------------------------------
            # final score
            # -------------------------------------------------
            total_score = my_gain - opponent_damage * OPPONENT_THREAT_WEIGHT
            if total_score > best_score:
                best_score = total_score
                best_action = {
                    "box": b,
                    "row": r,
                    "col": c,
                    "reason": (
                        f"{cand.get('reason', '')} "
                        f"(Medium Eval: {my_gain:.2f} / "
                        f"Enemy Threat: -{opponent_damage:.2f})"
                    )
                }

        # final fallback
        return best_action or fallback_move(legal_moves)