import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models import Move, ModeSetting, ArenaStepRequest
from helper import get_state, run_ai_turn
from engine.engine import UltimateTicTacToeEngine
from arena.pool import AgentPool

import logging

logger = logging.getLogger("uvicorn.error")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = UltimateTicTacToeEngine()
agent_pool = AgentPool()
agent_list = agent_pool.get_pool_list()

# default: LLM easy
current_mode = "easy"

# -----------------------
# API Endpoints
# -----------------------

@app.get("/state")
def state():
    return get_state(engine)

@app.post("/set-mode")
def set_mode(setting: ModeSetting):
    global current_mode
    print(setting.mode)
    if setting.mode in ["easy", "medium", "minimax", "mcts"]:
        current_mode = setting.mode
        return {"status": "success", "current_mode": current_mode}
    return {"status": "error", "message": "Invalid mode setting"}

@app.post("/move")
def move(m: Move):
    success = engine.make_move(m.box, m.row, m.col, player=1)
    ai_info = None

    if success and engine.check_game_over() == 0:
        current_agent = agent_pool.get_agent(current_mode)
        total_pieces = sum(1 for b in range(9) for r in range(3) for c in range(3) if engine.board[b][r][c] != 0)
        ai_player_id = 1 if total_pieces % 2 == 0 else 2
        ai_action = run_ai_turn(engine, current_agent, current_player=ai_player_id)
        ai_info = {
            "box": ai_action.get("box"),
            "row": ai_action.get("row"),
            "col": ai_action.get("col"),
            "reason": ai_action.get("reason", "No reason provided")
        }
        
    return {
        "success": success,
        "state": get_state(engine), 
        "ai_info": ai_info
    }

@app.post("/ai-move")
def ai_move():
    current_agent = agent_pool.get_agent(current_mode)
    total_pieces = sum(1 for b in range(9) for r in range(3) for c in range(3) if engine.board[b][r][c] != 0)
    ai_player_id = 1 if total_pieces % 2 == 0 else 2
    
    action = run_ai_turn(engine, current_agent, current_player=ai_player_id)
    return {"ai_action": action, "state": get_state(engine)}

@app.post("/reset")
def reset():
    global engine
    engine = UltimateTicTacToeEngine()
    agent_pool.prepare_for_new_game()
    return get_state(engine)

@app.post("/arena-step")
def arena_step(request: ArenaStepRequest):
    if engine.check_game_over() != 0:
        return {"game_over": True, "winner": engine.check_game_over(), "state": get_state(engine)}
        
    legal = engine.get_legal_moves()
    
    # Determine current player based on the number of pieces on the board
    total_pieces = sum(1 for b in range(9) for r in range(3) for c in range(3) if engine.board[b][r][c] != 0)
    current_player = 1 if total_pieces % 2 == 0 else 2
    
    if total_pieces == 0:
        agent_pool.prepare_for_new_game()
    
    chosen_mode = request.p1_mode if current_player == 1 else request.p2_mode
    active_arena_agent = agent_pool.get_arena_agent(chosen_mode, player_id=current_player)
    action = active_arena_agent.get_move(engine, legal)
    
    ai_choice = (action.get("box"), action.get("row"), action.get("col"))
    if ai_choice not in legal:
        fallback_move = legal[0]
        action["box"], action["row"], action["col"] = fallback_move
        action["reason"] = f"[{active_arena_agent.name} Hallucinated] Forced fallback."
    engine.make_move(action["box"], action["row"], action["col"], player=current_player)
    
    return {
        "game_over": False,
        "current_player": current_player,
        "agent_name": active_arena_agent.name,
        "ai_info": action,
        "state": get_state(engine)
    }