import ollama
import json

class LLMAgent:
    def __init__(self, model_name="llama3"):
        self.model = model_name

    def build_prompt(self, engine_state_str: str, legal_moves: list):
        # 這裡加入一點點 System Prompt 給模型定錨
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

    def get_move(self, prompt):
        """呼叫 Ollama"""
        response = ollama.chat(model=self.model, messages=[
            {'role': 'user', 'content': prompt}
        ])
        
        # 簡單的 JSON 解析，防呆
        try:
            content = response['message']['content']
            # 萬一模型吐出 Markdown (```json ... ```)，這裡要處理一下
            clean_content = content.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_content)
        except:
            return {"error": "Invalid format", "raw": response['message']['content']}   