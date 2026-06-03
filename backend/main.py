import sys
import os
import threading
from typing import Dict

gpu_lock = threading.Lock()

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
games: Dict[str, dict] = {}

# default: LLM easy
current_mode = "easy"

def get_or_create_game(session_id: str) -> dict:
    if not session_id:
        session_id = "default_room"
        
    if session_id not in games:
        games[session_id] = {
            "engine": UltimateTicTacToeEngine(),
            "mode": "easy"
        }
    return games[session_id]

# -----------------------
# API Endpoints
# -----------------------

@app.get("/state")
def state(session_id: str = "default_room"):
    game = get_or_create_game(session_id)
    return get_state(game["engine"])

@app.post("/set-mode")
def set_mode(setting: ModeSetting, session_id: str = "default_room"):
    if setting.mode in ["easy", "medium", "minimax", "mcts", "rl"]:
        game = get_or_create_game(session_id)
        game["mode"] = setting.mode
        return {"status": "success", "current_mode": game["mode"]}
    return {"status": "error", "message": "Invalid mode setting"}

@app.post("/move")
def move(m: Move, session_id: str = "default_room"):
    with gpu_lock:
        game = get_or_create_game(session_id)
        current_engine = game["engine"]
        current_mode = game["mode"]
        
        success = current_engine.make_move(m.box, m.row, m.col, player=1)
        ai_info = None

        if success and current_engine.check_game_over() == 0:
            current_agent = agent_pool.get_agent(current_mode)
            total_pieces = sum(1 for b in range(9) for r in range(3) for c in range(3) if current_engine.board[b][r][c] != 0)
            ai_player_id = 1 if total_pieces % 2 == 0 else 2
            ai_action = run_ai_turn(current_engine, current_agent, current_player=ai_player_id)
            ai_info = {
                "box": ai_action.get("box"),
                "row": ai_action.get("row"),
                "col": ai_action.get("col"),
                "reason": ai_action.get("reason", "No reason provided")
            }
            
        return {
            "success": success,
            "state": get_state(current_engine), 
            "ai_info": ai_info
        }

@app.post("/ai-move")
def ai_move(session_id: str = "default_room"):
    with gpu_lock:
        game = get_or_create_game(session_id)
        current_engine = game["engine"]
        current_mode = game["mode"]
        
        current_agent = agent_pool.get_agent(current_mode)
        total_pieces = sum(1 for b in range(9) for r in range(3) for c in range(3) if current_engine.board[b][r][c] != 0)
        ai_player_id = 1 if total_pieces % 2 == 0 else 2
        
        action = run_ai_turn(current_engine, current_agent, current_player=ai_player_id)
        return {"ai_action": action, "state": get_state(current_engine)}

@app.post("/reset")
def reset(session_id: str = "default_room"):
    with gpu_lock:
        if session_id in games:
            games[session_id]["engine"] = UltimateTicTacToeEngine()
        else:
            get_or_create_game(session_id)
            
        agent_pool.prepare_for_new_game()
        return get_state(games[session_id]["engine"])

@app.post("/arena-step")
def arena_step(request: ArenaStepRequest, session_id: str = "default_room"):
    with gpu_lock:
        game = get_or_create_game(session_id)
        current_engine = game["engine"]
        
        if current_engine.check_game_over() != 0:
            return {"game_over": True, "winner": current_engine.check_game_over(), "state": get_state(current_engine)}
            
        legal = current_engine.get_legal_moves()
        total_pieces = sum(1 for b in range(9) for r in range(3) for c in range(3) if current_engine.board[b][r][c] != 0)
        current_player = 1 if total_pieces % 2 == 0 else 2
        
        if total_pieces == 0:
            agent_pool.prepare_for_new_game()
        
        chosen_mode = request.p1_mode if current_player == 1 else request.p2_mode
        active_arena_agent = agent_pool.get_arena_agent(chosen_mode, player_id=current_player)
        action = active_arena_agent.get_move(current_engine, legal)
        
        ai_choice = (action.get("box"), action.get("row"), action.get("col"))
        if ai_choice not in legal:
            fallback_move = legal[0]
            action["box"], action["row"], action["col"] = fallback_move
            action["reason"] = f"[{active_arena_agent.name} Hallucinated] Forced fallback."
        current_engine.make_move(action["box"], action["row"], action["col"], player=current_player)
        
        return {
            "game_over": False,
            "current_player": current_player,
            "agent_name": active_arena_agent.name,
            "ai_info": action,
            "state": get_state(current_engine)
        }