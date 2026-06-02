from ollama import Client
import re

class PhiEvaluator:
    def __init__(self, model="phi4-mini"):
        self.model = model
        self.client = Client(host="http://127.0.0.1:11434")

    def evaluate(self, engine) -> float:
        state_str = engine.to_llm_string()
        prompt = f"""You are a state evaluator for Ultimate Tic-Tac-Toe.
Your task is to evaluate the board state. Assume both players play optimally.

You must output a single valid JSON object containing exactly one key "score".
The "score" value must be a single integer in the range [-100, 100].

Scoring anchors:
    +100 = immediate win for AI
    +50 = strong advantage
    0 = equal position
    -50 = opponent advantage
    -100 = opponent winning

Evaluate symmetrically and avoid bias toward negative scores.

Focus on:
  1. Global board advantage (won sub-boards)
  2. Immediate threats (forced wins/losses)
  3. Control of key sub-boards
  4. Mobility and future options

You must STRICTLY follow this JSON format. Do not include any reasoning, markdown fences, or extra text.

Example Output:
{{
    "score": 15
}}

Board state:
{state_str}
"""

        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                format="json",  
                options={
                    "temperature": 0.0  
                }
            )
            
            import json
            data = json.loads(response['response'].strip())
            score = float(data.get("score", 0))
            return max(-100.0, min(100.0, score))
            
        except Exception as e:
            import sys
            sys.stderr.write(f"⚠️ [PhiEvaluator Error] {str(e)}. Fallback to score 0.\n")
            return 0.0