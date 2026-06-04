# src/arena.py
import sys
import time
from typing import List, Tuple
from tqdm import tqdm
from engine.engine import UltimateTicTacToeEngine

class ArenaAgent:
    def __init__(self, agent_instance, name: str = "AI_Agent"):
        self.agent = agent_instance
        self.name = name

    def get_move(self, engine: UltimateTicTacToeEngine, legal_moves: List[Tuple[int, int, int]]) -> dict:
        if hasattr(self.agent, "get_move"):
            return self.agent.get_move(engine, legal_moves)
        elif hasattr(self.agent, "predict"):
            move = self.agent.predict(engine)
            return {"box": move[0], "row": move[1], "col": move[2], "reason": "RL Model Prediction"}
        else:
            raise AttributeError(f"The provided agent instance in ArenaAgent('{self.name}') does not have a recognized decision method.")

class Arena:
    def __init__(self, p1: ArenaAgent, p2: ArenaAgent, agent_pool=None):
        self.p1 = p1
        self.p2 = p2
        self.agent_pool = agent_pool 
        
        self.stats = {
            "p1_wins": 0,
            "p2_wins": 0,
            "draws": 0,
            "total_games": 0,
            "p1_illegal_attempts": 0,
            "p2_illegal_attempts": 0,
            "game_lengths": [],        
            "p1_latencies": [],        
            "p2_latencies": [],        
        }

    def run_single_game(self, verbose=False) -> int:
        engine = UltimateTicTacToeEngine()
        
        if self.agent_pool and hasattr(self.agent_pool, "prepare_for_new_game"):
            self.agent_pool.prepare_for_new_game()
        else:
            for p_agent in [self.p1, self.p2]:
                if hasattr(p_agent.agent, "reset_agent"):
                    p_agent.agent.reset_agent(starting_player_id=1)
        
        if verbose:
            print(f"\n===== Game Start: {self.p1.name} (X) vs {self.p2.name} (O) =====")

        move_count = 0
        
        # 💡 初始化時先設定好起始描述
        with tqdm(total=81, desc=f"🕹️ Step 1 | Score: 0-0 (0D) | Next: {self.p1.name}", leave=False, disable=verbose) as pbar:
            while engine.check_game_over() == 0:
                legal_moves = engine.get_legal_moves()
                total_pieces = sum(1 for b in range(9) for r in range(3) for c in range(3) if engine.board[b][r][c] != 0)
                current_player = 1 if total_pieces % 2 == 0 else 2

                active_arena_agent = self.p1 if current_player == 1 else self.p2

                # -------------------------------------------------
                # 🧠 大模型長考區（這時候畫面會定格在上一手最後更新的比分）
                # -------------------------------------------------
                start_time = time.time()
                action = active_arena_agent.get_move(engine, legal_moves)
                latency = time.time() - start_time

                if current_player == 1:
                    self.stats["p1_latencies"].append(latency)
                else:
                    self.stats["p2_latencies"].append(latency)

                ai_choice = (action.get("box"), action.get("row"), action.get("col"))

                is_hallucination = False
                if ai_choice not in legal_moves:
                    is_hallucination = True
                    if current_player == 1:
                        self.stats["p1_illegal_attempts"] += 1
                    else:
                        self.stats["p2_illegal_attempts"] += 1
                    
                    fallback_move = legal_moves[0]
                    box, row, col = fallback_move[0], fallback_move[1], fallback_move[2]
                    if verbose:
                        sys.stderr.write(f"⚠️ [{active_arena_agent.name}] Hallucination! Wanted {ai_choice}. Forced fallback to {fallback_move}.\n")
                else:
                    box, row, col = ai_choice[0], ai_choice[1], ai_choice[2]

                # 💡 執行落子，此時大盤狀態正式改變！
                engine.make_move(box, row, col, player=current_player)
                if not hasattr(engine, "history"):
                    engine.history = []
                engine.history.append((box, row, col, current_player))
                
                move_count += 1
                
                # 抓出下一手準備要動的人是誰，提早顯示
                next_agent_name = self.p2.name if current_player == 1 else self.p1.name
                
                pbar.set_description(
                    f'🕹️ Step {move_count+1} | Score: {self.stats["p1_wins"]}-{self.stats["p2_wins"]} ({self.stats["draws"]}D) | Next: {next_agent_name}'
                )

                pbar.update(1)
                pbar.set_postfix({
                    "latency": f"{latency:.2f}s",
                    "hallu": "⚠️" if is_hallucination else "✅"
                })

                if verbose:
                    print(f"[{active_arena_agent.name}] Step {move_count} -> Box {box}, Row {row}, Col {col} | Latency: {latency:.3f}s | Reason: {action.get('reason', 'None')}")

        result = engine.check_game_over()
        if result == 1:
            self.stats["p1_wins"] += 1
        elif result == 2:
            self.stats["p2_wins"] += 1
        elif result == 3:
            self.stats["draws"] += 1
            
        self.stats["game_lengths"].append(move_count)
        return result

    def run_benchmark(self, num_games=20, verbose=False):
        for k in ["p1_wins", "p2_wins", "draws", "p1_illegal_attempts", "p2_illegal_attempts"]:
            self.stats[k] = 0
        self.stats["game_lengths"] = []
        self.stats["p1_latencies"] = []
        self.stats["p2_latencies"] = []
        self.stats["total_games"] = num_games

        print(f"Starting Benchmark Pipeline: {num_games} Games")
        
        for i in tqdm(range(num_games), desc="🏆 Simulating Matches"):
            self.run_single_game(verbose=verbose)

        p1_rate = (self.stats["p1_wins"] / num_games) * 100
        p2_rate = (self.stats["p2_wins"] / num_games) * 100
        draw_rate = (self.stats["draws"] / num_games) * 100

        avg_steps = sum(self.stats["game_lengths"]) / num_games if num_games > 0 else 0
        avg_p1_lat = sum(self.stats["p1_latencies"]) / len(self.stats["p1_latencies"]) if self.stats["p1_latencies"] else 0
        avg_p2_lat = sum(self.stats["p2_latencies"]) / len(self.stats["p2_latencies"]) if self.stats["p2_latencies"] else 0

        print("\n" + "="*60)
        print("EXPERIMENTAL BENCHMARK REPORT")
        print("="*60)
        print(f" Matchup: {self.p1.name} (P1) vs {self.p2.name} (P2)")
        print(f" Total Games Simulated: {num_games}")
        print(f" Avg. Game Length (Steps): {avg_steps:.1f} moves")
        print("-"*60)
        print(f"{self.p1.name} Wins: {self.stats['p1_wins']} ({p1_rate:.1f}%)")
        print(f"{self.p2.name} Wins: {self.stats['p2_wins']} ({p2_rate:.1f}%)")
        print(f"Draws: {self.stats['draws']} ({draw_rate:.1f}%)")
        print("-"*60)
        print(f"Avg. Latency per Move:")
        print(f"  - {self.p1.name} (P1): {avg_p1_lat:.4f} seconds")
        print(f"  - {self.p2.name} (P2): {avg_p2_lat:.4f} seconds")
        print("-"*60)
        print(f"Spatial Hallucinations:")
        print(f"  - {self.p1.name} (P1): {self.stats['p1_illegal_attempts']} times")
        print(f"  - {self.p2.name} (P2): {self.stats['p2_illegal_attempts']} times")
        print("="*60 + "\n")
        
        return self.stats