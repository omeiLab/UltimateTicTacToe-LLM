import sys
import re
import time
import queue
import threading
import subprocess
from dataclasses import dataclass, field

WIN_LINES = [
    (0,1,2),(3,4,5),(6,7,8),
    (0,3,6),(1,4,7),(2,5,8),
    (0,4,8),(2,4,6),
]

COORD_RE = re.compile(r"^\s*(?:MOVE\s+)?(-?\d+)\s+(-?\d+)\s*$", re.I)

@dataclass
class Board:
    big: list = field(default_factory=lambda:[0]*9)
    state: list = field(default_factory=lambda:[[0]*9 for _ in range(9)])
    can_place: list = field(default_factory=lambda:[[True]*9 for _ in range(9)])
    nxt: int = 1

    def check_win(self):
        for a,b,c in WIN_LINES:
            if self.big[a] == self.big[b] == self.big[c] and self.big[a] > 0:
                return self.big[a]
        cnt = 0
        for x in self.big:
            if x != 0:
                cnt += 1
        if cnt == 9:
            return -1
        return 0

    def update(self,chunk,idx):
        finish = False
        for i in range(9):
            for j in range(9):
                self.can_place[i][j] = False
        for a,b,c in WIN_LINES:
            if self.state[chunk][a] == self.state[chunk][b] == self.state[chunk][c] and self.state[chunk][a] != 0:
                finish = True
        if finish:
            self.big[chunk] = self.nxt
        cnt_small = 0
        for i in range(9):
            if self.state[chunk][i] != 0:
                cnt_small += 1
        if self.big[chunk] == 0 and cnt_small == 9:
            self.big[chunk] = -1
        if self.big[idx] != 0:
            for i in range(9):
                if self.big[i] != 0:
                    continue
                for j in range(9):
                    if self.state[i][j] == 0:
                        self.can_place[i][j] = True
        else:
            for i in range(9):
                if self.state[idx][i] == 0:
                    self.can_place[idx][i] = True

    def legal_global(self,row,col):
        if row < 0 or row >= 9 or col < 0 or col >= 9:
            return False
        x = row//3*3 + col//3
        y = row%3*3 + col%3
        return self.can_place[x][y]

    def place_global(self,row,col):
        if not self.legal_global(row,col):
            return False
        x = row//3*3 + col//3
        y = row%3*3 + col%3
        self.state[x][y] = self.nxt
        self.update(x,y)
        self.nxt ^= 3
        return True

    def board_text(self):
        out = []
        out.append("  012 345 678")
        out.append("  --- --- ---")
        for l in range(3):
            for i in range(3):
                s = str(l*3+i)+"|"
                for j in range(3):
                    for k in range(3):
                        v = self.state[l*3+j][i*3+k]
                        if v == 1:
                            s += "O"
                        elif v == 2:
                            s += "X"
                        else:
                            s += " "
                    s += "|"
                out.append(s)
            out.append("  --- --- ---")
        return "\n".join(out)

@dataclass
class Model:
    name: str
    raw_cmd: str
    proc: subprocess.Popen = None
    q: queue.Queue = None
    threads: list = field(default_factory=list)

    def start(self,is_first,log):
        self.q = queue.Queue()
        self.proc = subprocess.Popen(
            self.raw_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            shell=True,
        )
        def reader(stream,kind):
            try:
                for line in stream:
                    self.q.put((kind,line.rstrip("\n").rstrip("\r")))
            except Exception as e:
                self.q.put((kind,f"<reader error: {e}>"))
        for kind,stream in (("stdout",self.proc.stdout),("stderr",self.proc.stderr)):
            th = threading.Thread(target=reader,args=(stream,kind),daemon=True)
            th.start()
            self.threads.append(th)

        init_value = 1 if is_first else 0
        self.send(f"{init_value}\n")
        log.write(f"[{self.name}] start side={'O(first)' if is_first else 'X(second)'}, init={init_value}, cmd={self.raw_cmd}\n")

    def send(self,s):
        if self.proc is None or self.proc.stdin is None:
            return False
        try:
            self.proc.stdin.write(s)
            self.proc.stdin.flush()
            return True
        except Exception:
            return False

    def stop(self):
        if self.proc is None:
            return
        try:
            self.send("-1 -1\n")
        except Exception:
            pass
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.wait(timeout=0.2)
        except Exception:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=0.5)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass

def strip_prefix(cmd):
    low = cmd.lower().strip()
    for key in ("cpp:","py:","protocol:","coord:"):
        if low.startswith(key):
            return cmd[len(key):]
    return cmd

def parse_coord(line):
    m = COORD_RE.match(line)
    if not m:
        return None
    return int(m.group(1)),int(m.group(2))

def read_move(model,timeout_ms,log):
    deadline = time.time() + timeout_ms/1000.0
    while True:
        remain = deadline-time.time()
        if remain <= 0:
            return None,"timeout"
        if model.proc.poll() is not None and model.q.empty():
            return None,f"process exited with code {model.proc.returncode}"
        try:
            kind,line = model.q.get(timeout=min(0.05,remain))
        except queue.Empty:
            continue
        log.write(f"[{model.name} {kind}] {line}\n")
        if kind != "stdout":
            continue
        coord = parse_coord(line)
        if coord is not None:
            return coord,None

def play_game(game_id,cmds,timeout_ms,show_board,log):
    board = Board()
    models = [Model("ai0",cmds[0]),Model("ai1",cmds[1])]

    # even games: ai0 is first/O, ai1 is second/X
    # odd games: ai1 is first/O, ai0 is second/X
    side_to_ai = [0,1]
    if game_id % 2 == 1:
        side_to_ai = [1,0]

    ai_to_side = [0,0]
    ai_to_side[side_to_ai[0]] = 0
    ai_to_side[side_to_ai[1]] = 1

    log.write(f"\n===== game {game_id} =====\n")
    log.write(f"O(first)=ai{side_to_ai[0]}, X(second)=ai{side_to_ai[1]}\n")

    for i in range(2):
        models[i].start(is_first=(ai_to_side[i] == 0),log=log)

    fail = None
    winner = 0
    move_id = 0
    try:
        while board.check_win() == 0:
            side = board.nxt-1
            ai = side_to_ai[side]
            model = models[ai]
            log.write(f"\nmove {move_id}: ai{ai} ({'O' if side==0 else 'X'}) to move\n")

            coord,err = read_move(model,timeout_ms,log)
            if err is not None:
                fail = f"ai{ai} failed: {err}"
                break

            row,col = coord
            log.write(f"[judge] ai{ai} move = {row} {col}\n")
            if not board.legal_global(row,col):
                fail = f"ai{ai} illegal move: {row} {col}"
                break

            board.place_global(row,col)
            if show_board:
                log.write(board.board_text()+"\n")

            res = board.check_win()
            if res != 0:
                winner = res
                break

            other_ai = side_to_ai[1-side]
            ok = models[other_ai].send(f"{row} {col}\n")
            log.write(f"[judge] send to ai{other_ai}: {row} {col}\n")
            if not ok:
                fail = f"failed to send move to ai{other_ai}"
                break

            move_id += 1

        if fail is None:
            if winner == 0:
                winner = board.check_win()
            log.write(f"[result] winner={winner}\n")
            if winner == -1:
                return "draw"
            if winner in (1,2):
                return f"ai{side_to_ai[winner-1]}"
            return "draw"

        log.write(f"[fail] {fail}\n")
        return "fail"
    finally:
        for m in models:
            m.stop()

def usage():
    print("usage:")
    print("  python battle_mix.py <ai0_cmd> <ai1_cmd> <log_file> [games] [timeout_ms] [show_board]")
    print("")
    print("AI protocol:")
    print("  first input line: 0 = this AI plays second, 1 = this AI plays first")
    print("  when the AI moves, it prints exactly one coordinate line: row col")
    print("  when the opponent moves, it reads one coordinate line: row col")
    print("  game end signal sent by judge: -1 -1")
    print("")
    print("examples:")
    print(r"  python battle_mix.py .\mcts_attack.exe .\mcts_defense.exe battle.log 10 120000 0")
    print(r"  python battle_mix.py .\mcts_attack.exe " + '"python -u .\\python\\mcts_defense_protocol.py"' + r" battle.log 10 120000 0")
    print(r"  python battle_mix.py " + '"python -u .\\a.py" "python -u .\\b.py"' + r" battle.log 10 120000 0")
    print("")
    print("optional prefixes cpp:, py:, protocol:, coord: are accepted but only stripped; they do not change protocol.")

def main():
    if len(sys.argv) < 4:
        usage()
        return
    cmd0 = strip_prefix(sys.argv[1])
    cmd1 = strip_prefix(sys.argv[2])
    log_file = sys.argv[3]
    games = int(sys.argv[4]) if len(sys.argv) >= 5 else 1
    timeout_ms = int(sys.argv[5]) if len(sys.argv) >= 6 else 120000
    show_board = int(sys.argv[6]) if len(sys.argv) >= 7 else 1

    score = {"ai0":0,"ai1":0,"draw":0,"fail":0}
    with open(log_file,"w",encoding="utf-8") as log:
        log.write(f"ai0 cmd={cmd0}\n")
        log.write(f"ai1 cmd={cmd1}\n")
        log.write(f"games={games}, timeout_ms={timeout_ms}, show_board={show_board}\n")
        log.write("protocol: first input 0=AI second, 1=AI first; stdout coordinate row col\n")
        for g in range(games):
            res = play_game(g,[cmd0,cmd1],timeout_ms,show_board,log)
            score[res] += 1
            log.write(f"[game {g} summary] {res}\n")
        log.write("\n===== summary =====\n")
        log.write(f"ai0 win: {score['ai0']}\n")
        log.write(f"ai1 win: {score['ai1']}\n")
        log.write(f"draw: {score['draw']}\n")
        log.write(f"fail: {score['fail']}\n")

    print(f"done. log = {log_file}")
    print(f"ai0 win: {score['ai0']}, ai1 win: {score['ai1']}, draw: {score['draw']}, fail: {score['fail']}")

if __name__ == "__main__":
    main()
