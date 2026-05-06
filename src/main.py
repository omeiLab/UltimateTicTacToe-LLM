from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from engine import UltimateTicTacToeEngine
from llm_agent import LLMAgent

app = FastAPI()

# 🔥 讓 React 可以連（很重要）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = UltimateTicTacToeEngine()
agent = LLMAgent()

# -----------------------
# Models
# -----------------------

class Move(BaseModel):
    box: int
    row: int
    col: int

# -----------------------
# Helpers
# -----------------------

def get_state():
    return {
        "board": engine.board,
        "big_board": engine.big_board,
        "active_box": engine.active_box,
        "legal_moves": engine.get_legal_moves()
    }

def run_ai_turn():
    # 這是你原本 /ai-move 的邏輯
    state_str = engine.to_llm_string()
    legal = engine.get_legal_moves()
    prompt = agent.build_prompt(state_str, legal)
    action = agent.get_move(prompt)
    if "box" in action:
        engine.make_move(action["box"], action["row"], action["col"], player=2)
    return action

# -----------------------
# API
# -----------------------

@app.get("/state")
def state():
    return get_state()


@app.post("/move")
def move(m: Move):
    success = engine.make_move(m.box, m.row, m.col, player=1)
    
    ai_info = None
    if success and engine.check_game_over() == 0:
        ai_action = run_ai_turn()
        ai_info = {
            "box": ai_action.get("box"),
            "row": ai_action.get("row"),
            "col": ai_action.get("col"),
            "reason": ai_action.get("reason", "No reason provided")
        }
        
    return {
        "success": success,
        "state": get_state(),
        "ai_info": ai_info
    }

@app.post("/ai-move")
def ai_move():
    action = run_ai_turn()
    return {"ai_action": action, "state": get_state()}

@app.post("/reset")
def reset():
    global engine
    engine = UltimateTicTacToeEngine()

    return get_state()