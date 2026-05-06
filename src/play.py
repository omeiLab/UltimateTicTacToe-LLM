from engine import UltimateTicTacToeEngine
from llm_agent import LLMAgent

def play():
    engine = UltimateTicTacToeEngine()
    agent = LLMAgent()
    
    print("=== 遊戲開始：你 (X) vs LLM (O) ===")
    print("輸入格式：box row col (例如: 4 1 1 表示 box 4, row 1, col 1)")
    
    player_turn = True # True: Human, False: AI
    
    while True:
        print(engine) # 這是我們之前寫的 __str__
        
        if player_turn:
            user_input = input("你的回合 (box row col): ").split()
            if len(user_input) != 3: continue
            box, r, c = map(int, user_input)
            
            if engine.make_move(box, r, c, 1):
                player_turn = False
            else:
                print("!! 非法步數，請重試 !!")
        else:
            print("AI 思考中...")
            state_str = engine.to_llm_string()
            moves = engine.get_legal_moves()
            prompt = agent.build_prompt(state_str, moves)
            
            ai_move = agent.get_move(prompt)
            
            # 簡單防錯處理
            if "box" in ai_move:
                b, r, c = ai_move['box'], ai_move['row'], ai_move['col']
                print(f"AI 下在: {b} {r} {c} (Reason: {ai_move.get('reason', 'None')})")
                if engine.make_move(b, r, c, 2):
                    player_turn = True
                else:
                    print("AI 嘗試了非法步數，跳過回合...")
                    player_turn = True
            else:
                print("AI 輸出解析失敗:", ai_move)
                break

        if engine.check_game_over() != 0:
            print(engine)
            result = engine.check_game_over()
            if result == 1:
                print("恭喜你贏了！")
            elif result == 2:
                print("AI 贏了！")
            else:
                print("平手！")
            break

if __name__ == "__main__":
    play()