from abc import ABC, abstractmethod
import json
import copy
import sys
import ollama

class BaseAgent(ABC):
    def __init__(self, model_name="qwen2.5:7b", phi_evaluator=None):
        self.model = model_name
        self.phi = phi_evaluator

    def _call_llm_and_parse_json(self, prompt: str) -> dict:
        """
        JSON Parsing Method (Shared Utility)
        """
        try:
            response = ollama.chat(model=self.model, messages=[{'role': 'user', 'content': prompt}])
            content = response['message']['content']
            
            # 清理 Markdown 的 JSON 外殼
            clean_content = content.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_content)
        except Exception as e:
            # 萬一模型噴了奇怪的格式，sys.stderr 會直接在終端機打印
            sys.stderr.write(f"🚨 [Ollama/Parser Error] Model failed to return valid JSON: {e}\n")
            return {"error": "parse_failed", "raw_content": content if 'content' in locals() else ""}
        
    @abstractmethod
    def build_prompt(self, engine_state_str: str, legal_moves: list) -> str:
        """
        Prompt Construction Method (Children Must Implement)
        """
        pass

    @abstractmethod
    def get_move(self, engine, legal_moves: list) -> dict:
        """
        Move Generation Method (Children Must Implement)
        """
        pass