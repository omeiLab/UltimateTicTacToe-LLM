from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from engine import UltimateTicTacToeEngine
from phi_evaluator import PhiEvaluator
from arena import ArenaAgent

# 💡 從你拆開的兩個獨立檔案精準引入對應的 Agent 
from easy_agent import EasyAgent
from medium_agent import MediumAgent

import logging

logger = logging.getLogger("uvicorn.error")

app = FastAPI()

# 🔥 讓 React 可以連（維持跨域支援）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = UltimateTicTacToeEngine()

# Phi evauluator for medium & hard
phi_evaluator = PhiEvaluator(model="phi4-mini")

# 💡 建立大腦策略工廠字典，預設統一使用 qwen2.5:7b
agents = {
    "easy": EasyAgent(model_name="qwen2.5:7b"),
    "medium": MediumAgent(model_name="qwen2.5:7b", phi_evaluator=phi_evaluator),
}

p1_arena = ArenaAgent(agent_instance=agents["easy"], name="Qwen-Easy")
p2_arena = ArenaAgent(agent_instance=agents["medium"], name="Qwen-Medium")

# 全域難度狀態，預設為 easy 流派
current_mode = "easy"

# -----------------------
# Models
# -----------------------

class Move(BaseModel):
    box: int
    row: int
    col: int

# 新增：用於接收前端難度設定的 Pydantic Model
class ModeSetting(BaseModel):
    mode: str

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
    """整合多型調用的核心 AI 回合決策"""
    legal = engine.get_legal_moves()
    
    # 💡 核心亮點：根據當前設定，動態抓取對應大腦 (Polymorphism)
    current_agent = agents[current_mode]
    action = current_agent.get_move(engine, legal)
    
    # 安全防禦機制：攔截任何可能發生的空間幻覺座標違規
    ai_choice = (action.get("box"), action.get("row"), action.get("col"))
    if ai_choice not in legal:
        fallback_move = legal[0] # 被抓包違規時，強制指派第一個合法步保底
        action["box"] = fallback_move[0]
        action["row"] = fallback_move[1]
        action["col"] = fallback_move[2]
        action["reason"] = f"[Engine Corrected] AI wanted {ai_choice} ({action.get('reason')}), but it was ILLEGAL. Forced fallback."
    
    engine.make_move(action["box"], action["row"], action["col"], player=2)
    return action

# -----------------------
# API Endpoints
# -----------------------

@app.get("/state")
def state():
    return get_state()

@app.post("/set-mode")
def set_mode(setting: ModeSetting):
    """供前端切換遊戲難度的核心路由"""
    global current_mode
    if setting.mode in agents:
        current_mode = setting.mode
        return {"status": "success", "current_mode": current_mode}
    return {"status": "error", "message": "Invalid mode setting"}

@app.post("/move")
def move(m: Move):
    # 1. 玩家下棋
    success = engine.make_move(m.box, m.row, m.col, player=1)
    
    ai_info = None
    # 2. 玩家下完且遊戲尚未結束，連鎖觸發 AI 大腦
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

@app.post("/arena-step")
def arena_step():
    """讓前端逐步驅動的單步自動對打路由"""
    if engine.check_game_over() != 0:
        return {"game_over": True, "winner": engine.check_game_over(), "state": get_state()}
        
    legal = engine.get_legal_moves()
    
    # 精準判定當前輪到誰 (偶數P1, 奇數P2)
    total_pieces = sum(1 for b in range(9) for r in range(3) for c in range(3) if engine.board[b][r][c] != 0)
    current_player = 1 if total_pieces % 2 == 0 else 2
    
    active_arena_agent = p1_arena if current_player == 1 else p2_arena
    
    # 呼叫 get_action
    action = active_arena_agent.get_action(engine, legal)
    
    # 空間幻覺防守護欄 (維持你的完美白盒防守)
    ai_choice = (action.get("box"), action.get("row"), action.get("col"))
    if ai_choice not in legal:
        fallback_move = legal[0]
        action["box"], action["row"], action["col"] = fallback_move
        action["reason"] = f"[{active_arena_agent.name} Hallucinated] Forced fallback."
        
    # 執行落子
    engine.make_move(action["box"], action["row"], action["col"], player=current_player)
    
    return {
        "game_over": False,
        "current_player": current_player,
        "agent_name": active_arena_agent.name,
        "ai_info": action,
        "state": get_state()
    }