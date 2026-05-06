import pytest
import json
from src.llm_agent import LLMAgent

def test_llm_agent():
    agent = LLMAgent()
    
    mock_prompt = """
    You are a UTTT expert.
    Board: 
    Box0:[000000000] Box1:[000000000] Box2:[000000000] 
    Box3:[000000000] Box4:[001000000] Box5:[000000000]
    Box6:[000000000] Box7:[000000000] Box8:[000000000]
    Active Box: 4
    
    Valid Moves: [(4, 0, 0), (4, 0, 1), (4, 0, 2), (4, 1, 0), (4, 1, 2), (4, 2, 0), (4, 2, 1), (4, 2, 2)]
    
    Output ONLY valid JSON: {"box": int, "row": int, "col": int, "reason": "..."}
    DO NOT include any explanation outside the JSON. Just the JSON.
    For example, if you want to play at box 4, row 1, col 2, you may output: {"box": 4, "row": 1, "col": 2, "reason": "This move blocks opponent's winning path."}
    """
    result = agent.get_move(mock_prompt)
    print("Result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    assert "box" in result and "row" in result and "col" in result, "Missing keys in LLM response"