from .llm_agent import BaseAgent

class EasyAgent(BaseAgent):
    """
    Simple 1-depth LLM Agent for UTTT
    """

    def build_prompt(self, engine_state_str: str, legal_moves: list):
        return f"""
You are a professional Ultimate Tic-Tac-Toe player. Your goal is to win the game.

Before you output the JSON, you MUST check your move by following these steps:
1. Identify all empty cells in the active box.
2. Check if the opponent can win in the next turn (Threats).
3. If a Threat exists, your move MUST be one of the Threatening cells.
4. If you output a move that is NOT blocking a threat, you must justify why your move is better than blocking.
But don't tell we how to play, just output your move and reason in JSON format.

Game rules: You must play in the designated box if possible. 
        
Current Board State:
{engine_state_str}
        
Valid Moves (box, row, col):
{legal_moves}
        
Constraint:
1. Only pick from the Valid Moves above.
2. Output MUST be in valid JSON format: {{"box": int, "row": int, "col": int, "reason": "..."}}
3. DO NOT include any explanation outside the JSON. Just the JSON.

For example, if you want to play at box 4, row 1, col 2, you may output: {{"box": 4, "row": 1, "col": 2, "reason": "This move blocks opponent's winning path."\}}
"""

    def get_move(self, engine, legal_moves: list) -> dict:
        state_str = engine.to_llm_string()
        prompt = self.build_prompt(state_str, legal_moves)
        result = self._call_llm_and_parse_json(prompt)
        
        if "error" in result:
            result =  {
                "box": -1, "row": -1, "col": -1, 
                "reason": f"JSON Decode Failed. Raw output: {result['raw_content']}..."
            }
        
        return result