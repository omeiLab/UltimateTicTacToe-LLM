from ollama import Client
import re

class PhiEvaluator:
    def __init__(self, model="phi4-mini"):
        self.model = model
        self.client = Client(host="http://127.0.0.1:11434")

    def evaluate(self, engine) -> float:
        state_str = engine.to_llm_string()
        prompt = f"""
You are a state evaluator for Ultimate Tic-Tac-Toe.

Your task is to evaluate the board state. Assume both players play optimally.

Return ONLY one integer in range [-100, 100].

Scoring anchors:
    +100 = immediate win for AI
    +50 = strong advantage
    0 = equal position
    -50 = opponent advantage
    -100 = opponent winning

If unclear, return 0

Evaluate symmetrically and avoid bias toward negative scores.

Focus on:
  1. Global board advantage (won sub-boards)
  2. Immediate threats (forced wins/losses)
  3. Control of key sub-boards
  4. Mobility and future options

Do NOT explain. Do NOT output text.

Example outputs:
10
-25
0
Any output that is not a single integer will be considered invalid.

Board state:
{state_str}
"""

        response = self.client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            format="json",
            options={
                "temperature": 0,
                "top_p": 1,
            }
        )

        text = response["message"]["content"]
        # print("[PHI RAW OUTPUT]")
        # print(repr(text))

        # -------------------------------------------------
        # SAFE PARSER (IMPORTANT)
        # -------------------------------------------------

        try:
            return int(text)
        except:
            match = re.search(r"-?\d+", text)
            if match:
                return int(match.group())

            return 0