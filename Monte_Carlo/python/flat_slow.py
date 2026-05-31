import sys
import time
import random
import math
import os

rnd = random.Random(int(time.time()))
WIN_LINES = ((0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6))

class Board:
    __slots__ = ('big','state','can_place','nxt')
    def __init__(self):
        self.big = [0] * 9
        self.state = [[0] * 9 for _ in range(9)]
        self.can_place = [[True] * 9 for _ in range(9)]
        self.nxt = 1

    def copy(self):
        ret = Board.__new__(Board)
        ret.big = self.big[:]
        ret.state = [row[:] for row in self.state]
        ret.can_place = [row[:] for row in self.can_place]
        ret.nxt = self.nxt
        return ret

    def check_win(self):
        for a,b,c in WIN_LINES:
            if(self.big[a] == self.big[b] and self.big[b] == self.big[c] and self.big[a] > 0):
                return self.big[a]
        cnt = 0
        for i in range(9):
            if(self.big[i] != 0):
                cnt += 1
        if(cnt == 9):
            return -1
        return 0

    def update(self,chunk,idx):
        finish = False
        small = self.state[chunk]
        for a,b,c in WIN_LINES:
            if(small[a] == small[b] and small[b] == small[c] and small[a] != 0):
                finish = True
        for i in range(9):
            for j in range(9):
                self.can_place[i][j] = False
        if(finish):
            self.big[chunk] = self.nxt
        cnt_small = 0
        for i in range(9):
            if(self.state[chunk][i] != 0):
                cnt_small += 1
        if(self.big[chunk] == 0 and cnt_small == 9):
            self.big[chunk] = -1
        if(self.big[idx] != 0):
            for i in range(9):
                if(self.big[i] != 0):
                    continue
                for j in range(9):
                    if(self.state[i][j] == 0):
                        self.can_place[i][j] = True
        else:
            for i in range(9):
                if(self.state[idx][i] == 0):
                    self.can_place[idx][i] = True

    def place(self,x,y):
        if(not self.can_place[x][y]):
            return False
        self.state[x][y] = self.nxt
        self.update(x,y)
        self.nxt ^= 3
        return True

    def place_global(self,row,col):
        if(row < 0 or row >= 9 or col < 0 or col >= 9):
            return False
        x = row // 3 * 3 + col // 3
        y = row % 3 * 3 + col % 3
        return self.place(x,y)

def to_global(move):
    x,y = move
    return x // 3 * 3 + y // 3, x % 3 * 3 + y % 3

def get_moves(ret):
    v = []
    if(ret.check_win() != 0):
        return v
    for i in range(9):
        for j in range(9):
            if(ret.can_place[i][j]):
                v.append((i,j))
    return v


DEFAULT_ST = 1000
ST = int(os.environ.get('ST', DEFAULT_ST))
DEP = 1

def simulation(ret):
    ret = ret.copy()
    while(ret.check_win() == 0):
        v = get_moves(ret)
        if(len(v) == 0):
            break
        move = rnd.choice(v)
        ret.place(move[0],move[1])
    return ret.check_win()

def _find_bset_move_board(ret,dep):
    rank = []
    for i in range(9):
        for j in range(9):
            if(ret.can_place[i][j]):
                now = ret.copy()
                player = now.nxt
                now.place(i,j)
                if(dep > 0):
                    sub_move = _find_bset_move(now,dep-1)
                    if(sub_move is not None):
                        now.place(sub_move[0],sub_move[1])
                cnt = 1
                for _ in range(ST):
                    res = simulation(now)
                    if(res == player):
                        cnt += 2
                    elif(res == -1):
                        cnt += 1
                    else:
                        cnt -= 10
                rank.append((cnt,(i,j)))
    if(len(rank) == 0):
        return None
    rank.sort(key=lambda x:x[0])
    return rank[-1][1]

def _find_bset_move(ret,dep):
    return _find_bset_move_board(ret,dep)

def find_bset_move(ret):
    return _find_bset_move(ret,DEP)

def main():
    first_line = sys.stdin.readline()
    if(not first_line):
        return
    ai_side = int(first_line.strip()) ^ 1
    game = Board()
    turn = 0
    while(game.check_win() == 0):
        if(turn == ai_side):
            move = find_bset_move(game)
            if(move is None):
                print('-1 -1', flush=True)
                return
            game.place(move[0],move[1])
            row,col = to_global(move)
            print(row,col, flush=True)
        else:
            line = sys.stdin.readline()
            if(not line):
                return
            row,col = map(int,line.split())
            if(row < 0 or col < 0):
                return
            if(not game.place_global(row,col)):
                return
        turn ^= 1

if(__name__ == '__main__'):
    main()

