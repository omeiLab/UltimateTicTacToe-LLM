# src/arena.py
import sys
from typing import List, Tuple
from tqdm import tqdm
from engine import UltimateTicTacToeEngine

class ArenaAgent:
    """
    競技場專用 Agent 包裝器 (Decorator / Adapter)
    本質上就是將一個已經 initiate 好的任意 agent 包裝起來，對齊競技場的 get_action 接口。
    """
    def __init__(self, agent_instance, name: str = "AI_Agent"):
        self.agent = agent_instance
        self.name = name

    def get_action(self, engine: UltimateTicTacToeEngine, legal_moves: List[Tuple[int, int, int]]) -> dict:
        """
        對齊競技場的統一接口，動態調用底層真實 agent 的決策方法
        """
        # 💡 自動轉接：如果你原本的 LLM Agent 有 get_move 方法，就呼叫它
        if hasattr(self.agent, "get_move"):
            return self.agent.get_move(engine, legal_moves)
        
        # 💡 自動轉接：如果未來組員的 RL 模型是用特定的 predict 或 search 方法，可以直接在這邊擴充轉接
        elif hasattr(self.agent, "predict"):
            # 假設組員回傳 (b, r, c)，我們幫他包裝成競技場要的字典格式
            move = self.agent.predict(engine)
            return {"box": move[0], "row": move[1], "col": move[2], "reason": "RL Model Prediction"}
            
        # 🛑 保底：萬一什麼都沒有，丟出錯誤提示
        else:
            raise AttributeError(f"The provided agent instance in ArenaAgent('{self.name}') does not have a recognized decision method.")


class Arena:
    """
    自動對弈實驗流水線 (Experimental Pipeline)
    負責調度兩個 ArenaAgent 進行多局自動對抗，並統計學術實驗數據。
    """
    def __init__(self, p1: ArenaAgent, p2: ArenaAgent):
        self.p1 = p1
        self.p2 = p2
        
        # 統計數據指標
        self.stats = {
            "p1_wins": 0,
            "p2_wins": 0,
            "draws": 0,
            "total_games": 0,
            "p1_illegal_attempts": 0, # P1 空間幻覺次數
            "p2_illegal_attempts": 0  # P2 空間幻覺次數
        }

    def run_single_game(self, verbose=False) -> int:
        """執行單局自動對弈，回傳勝者代號 (1: P1, 2: P2, 3: Draw)"""
        engine = UltimateTicTacToeEngine()
        
        if verbose:
            print(f"\n===== Game Start: {self.p1.name} (X) vs {self.p2.name} (O) =====")

        while engine.check_game_over() == 0:
            legal_moves = engine.get_legal_moves()
            
            # 依據棋盤上現有的棋子總數精準判定當前輪到誰 (偶數P1, 奇數P2)
            total_pieces = sum(1 for b in range(9) for r in range(3) for c in range(3) if engine.board[b][r][c] != 0)
            current_player = 1 if total_pieces % 2 == 0 else 2

            active_arena_agent = self.p1 if current_player == 1 else self.p2

            # 呼叫包裝後的 get_action
            action = active_arena_agent.get_action(engine, legal_moves)
            ai_choice = (action.get("box"), action.get("row"), action.get("col"))

            # 🛑 核心防守：安全性檢查與幻覺計數
            if ai_choice not in legal_moves:
                if current_player == 1:
                    self.stats["p1_illegal_attempts"] += 1
                else:
                    self.stats["p2_illegal_attempts"] += 1
                
                # 強制執行第一個合法步保底，確保流水線絕不卡死
                fallback_move = legal_moves[0]
                box, row, col = fallback_move[0], fallback_move[1], fallback_move[2]
                if verbose:
                    sys.stderr.write(f"⚠️ [{active_arena_agent.name}] Hallucination! Wanted {ai_choice}. Forced fallback to {fallback_move}.\n")
            else:
                box, row, col = ai_choice[0], ai_choice[1], ai_choice[2]

            # 執行落子
            engine.make_move(box, row, col, player=current_player)

            if verbose:
                print(f"[{active_arena_agent.name}] played -> Box {box}, Row {row}, Col {col} | Reason: {action.get('reason', 'None')}")

        # 結算單局
        result = engine.check_game_over()
        if result == 1:
            self.stats["p1_wins"] += 1
        elif result == 2:
            self.stats["p2_wins"] += 1
        elif result == 3:
            self.stats["draws"] += 1
            
        return result

    def run_benchmark(self, num_games=20, verbose=False):
        """執行大規模對抗實驗，並產出標準的統計報表"""
        self.stats = {k: 0 for k in self.stats if k != "total_games"}
        self.stats["total_games"] = num_games

        print(f"Starting Benchmark Pipeline: {num_games} Games")
        
        for _ in tqdm(range(num_games), desc="Simulating Matches"):
            self.run_single_game(verbose=verbose)

        p1_rate = (self.stats["p1_wins"] / num_games) * 100
        p2_rate = (self.stats["p2_wins"] / num_games) * 100
        draw_rate = (self.stats["draws"] / num_games) * 100

        print("\n" + "="*50)
        print("EXPERIMENTAL BENCHMARK REPORT")
        print("="*50)
        print(f" Matchup: {self.p1.name} (P1) vs {self.p2.name} (P2)")
        print(f" Total Games Simulated: {num_games}")
        print("-"*50)
        print(f"{self.p1.name} Wins: {self.stats['p1_wins']} ({p1_rate:.1f}%)")
        print(f"{self.p2.name} Wins: {self.stats['p2_wins']} ({p2_rate:.1f}%)")
        print(f"Draws: {self.stats['draws']} ({draw_rate:.1f}%)")
        print("-"*50)
        print(f"{self.p1.name} Spatial Hallucinations: {self.stats['p1_illegal_attempts']} times")
        print(f"{self.p2.name} Spatial Hallucinations: {self.stats['p2_illegal_attempts']} times")
        print("="*50 + "\n")
        
        return self.stats