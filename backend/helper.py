from typing import Dict, Any

def get_state(engine) -> Dict[str, Any]:
    return {
        "board": engine.board,
        "big_board": engine.big_board,
        "active_box": engine.active_box,
        "legal_moves": engine.get_legal_moves()
    }

def run_ai_turn(engine, current_agent, current_player: int) -> Dict[str, Any]:
    print(f"📡 [DEBUG] 當前出手的大腦類別是: {type(current_agent)}，它是: {getattr(current_agent, 'model_player', '無角色')}")
    legal = engine.get_legal_moves()
    action = current_agent.get_move(engine, legal)
    
    # Safe defense mechanism: Intercept any potential illegal move from the AI
    ai_choice = (action.get("box"), action.get("row"), action.get("col"))
    if ai_choice not in legal:
        fallback_move = legal[0]
        action["box"] = fallback_move[0]
        action["row"] = fallback_move[1]
        action["col"] = fallback_move[2]
        action["reason"] = f"[Engine Corrected] AI wanted {ai_choice} ({action.get('reason')}), but it was ILLEGAL. Forced fallback."
    
    # Make the move
    # current_player = 1 or 2
    engine.make_move(action["box"], action["row"], action["col"], player=current_player)
    return action

