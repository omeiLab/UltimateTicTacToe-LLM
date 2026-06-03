import subprocess
import os
import sys
from typing import List, Tuple

class MCTSAdapter:
    def __init__(self, exe_name: str = "mcts_ai", model_player: str = "O"):
        """
        model_player: X (ID=1), "O" (ID=2)
        """
        self.cpp_path = "../Monte_Carlo/cpp/mcts_balance.cpp"
        self.exe_name = exe_name
        self.model_player = model_player
        self.process = None
        self.exe_path = f"./{exe_name}.exe" if os.name == 'nt' else f"./{exe_name}"
        
        # compile C++ source code into an executable
        self._compile_cpp()

    def _compile_cpp(self):
        print(f"[MCTS Adapter] Compiling {self.cpp_path}...")
        try:
            result = subprocess.run(
                ["g++", self.cpp_path, "-o", self.exe_name], 
                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            print("[MCTS Adapter] C++ Compilation successful!")
        except subprocess.CalledProcessError as e:
            sys.stderr.write(f"[MCTS Adapter] Compilation failed: {e.stderr.decode()}\n")

    def reset_agent(self, starting_player_id: int = 1):
        """
        Reset the MCTS agent for a new game.
        """
        # Terminate any existing process to ensure a clean slate for the new game
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.process = None

        # Start the C++ MCTS executable as a subprocess with piped stdin and stdout for communication
        self.process = subprocess.Popen(
            [self.exe_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1   
        )

        is_first_mover = "1" if self.model_player == "X" else "0"
        self.process.stdin.write(f"{is_first_mover}\n")
        self.process.stdin.flush()
        
        print(f"[MCTS Adapter] Program started as {'FIRST(X)' if is_first_mover == '1' else 'SECOND(O)'} mover.")

        self.opening_move_buffered = None
        if is_first_mover == "1":
            out_line = self.process.stdout.readline().strip()
            if out_line:
                big, small = map(int, out_line.split())
                self.opening_move_buffered = (big, small)

    def _to_mcts_coord(self, b: int, r: int, c: int) -> Tuple[int, int]:
        row = (b // 3) * 3 + r
        col = (b % 3) * 3 + c
        return row, col

    def _from_mcts_coord(self, row: int, col: int) -> Tuple[int, int, int]:
        big_row = row // 3
        big_col = col // 3
        b = big_row * 3 + big_col
        r = row % 3
        c = col % 3
        return b, r, c

    def get_move(self, engine, legal_moves: List[Tuple[int, int, int]]) -> dict:
        # safeguard
        if self.process is None or self.process.poll() is not None:
            self.reset_agent(starting_player_id=1)

        try:
            if self.model_player == "X" and self.opening_move_buffered is not None:
                big, small = self.opening_move_buffered
                self.opening_move_buffered = None
                b, r, c = self._from_mcts_coord(big, small)
                return {"box": b, "row": r, "col": c, "reason": "[MCTS C++] default opening move from MCTS (first mover)"}

            if not hasattr(engine, "history") or not engine.history:
                fallback_opp = legal_moves[0]
                opp_b, opp_r, opp_c = fallback_opp[0], fallback_opp[1], fallback_opp[2]
            else:
                opp_b, opp_r, opp_c, _ = engine.history[-1]

            opp_big, opp_small = self._to_mcts_coord(opp_b, opp_r, opp_c)
            self.process.stdin.write(f"{opp_big} {opp_small}\n")
            self.process.stdin.flush()

            out_line = self.process.stdout.readline().strip()
            if not out_line:
                raise RuntimeError("C++ MCTS process did not return a move.") 

            big, small = map(int, out_line.split())
            b, r, c = self._from_mcts_coord(big, small)
            
            return {
                "box": b,
                "row": r,
                "col": c,
                "reason": f"[MCTS C++] Input: ({opp_big},{opp_small}) -> Output: ({big},{small})"
            }

        except Exception as e:
            fallback = legal_moves[0]
            return {
                "box": fallback[0],
                "row": fallback[1],
                "col": fallback[2],
                "reason": f"[MCTS Fallback] Error: ({str(e)})"
            }

    def __del__(self):
        if self.process:
            self.process.terminate()