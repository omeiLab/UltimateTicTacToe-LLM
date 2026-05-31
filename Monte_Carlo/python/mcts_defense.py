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


DEFAULT_ST = 50000
ST = int(os.environ.get('ST', DEFAULT_ST))
MCTS_C = 2.0
DRAW_SCORE = 0.8
ROLLOUT_TYPE = 2
FINAL_TYPE = 0

class Node:
    __slots__ = ('b','move','parent','visit','win','child','untry')
    def __init__(self):
        self.b = None
        self.move = (-1,-1)
        self.parent = -1
        self.visit = 0
        self.win = 0.0
        self.child = []
        self.untry = []

def cell_weight(x):
    if(ROLLOUT_TYPE == 0):
        return 1
    if(ROLLOUT_TYPE == 1):
        if(x == 4):
            return 8
        if(x == 0 or x == 2 or x == 6 or x == 8):
            return 4
        return 1
    if(x == 4):
        return 5
    if(x == 1 or x == 3 or x == 5 or x == 7):
        return 3
    return 2

def get_random_move(v):
    total = 0
    for p in v:
        total += cell_weight(p[1])
    x = rnd.randrange(total)
    for p in v:
        x -= cell_weight(p[1])
        if(x < 0):
            return p
    return v[-1]

def simulation(ret):
    ret = ret.copy()
    while(ret.check_win() == 0):
        v = get_moves(ret)
        if(len(v) == 0):
            break
        move = get_random_move(v)
        ret.place(move[0],move[1])
    return ret.check_win()

def get_score(res,player):
    if(res == player):
        return 1.0
    if(res == -1):
        return DRAW_SCORE
    return 0.0

def select_child(tree,u):
    best = -1
    best_val = -10**100
    C = MCTS_C
    for v in tree[u].child:
        if(tree[v].visit == 0):
            return v
        avg = tree[v].win / tree[v].visit
        val = avg + C * math.sqrt(math.log(tree[u].visit + 1.0) / tree[v].visit)
        if(val > best_val):
            best_val = val
            best = v
    return best

def find_bset_move(ret):
    tree = []
    root = Node()
    root.b = ret.copy()
    root.untry = get_moves(ret)
    tree.append(root)
    for _ in range(ST):
        u = 0
        while(len(tree[u].untry) == 0 and len(tree[u].child) > 0):
            u = select_child(tree,u)
        if(tree[u].b.check_win() == 0 and len(tree[u].untry) > 0):
            idx = rnd.randrange(len(tree[u].untry))
            move = tree[u].untry[idx]
            tree[u].untry[idx] = tree[u].untry[-1]
            tree[u].untry.pop()
            nxt_board = tree[u].b.copy()
            nxt_board.place(move[0],move[1])
            nxt_node = Node()
            nxt_node.b = nxt_board
            nxt_node.move = move
            nxt_node.parent = u
            nxt_node.untry = get_moves(nxt_board)
            tree.append(nxt_node)
            tree[u].child.append(len(tree)-1)
            u = len(tree)-1
        res = simulation(tree[u].b)
        while(u != -1):
            tree[u].visit += 1
            if(tree[u].move[0] != -1):
                player = tree[u].b.nxt ^ 3
                tree[u].win += get_score(res,player)
            u = tree[u].parent
    best = -1
    for v in tree[0].child:
        if(best == -1):
            best = v
        elif(FINAL_TYPE == 0):
            if(tree[v].visit > tree[best].visit):
                best = v
        else:
            a = tree[v].win / max(1,tree[v].visit)
            b = tree[best].win / max(1,tree[best].visit)
            if(a > b or (a == b and tree[v].visit > tree[best].visit)):
                best = v
    if(best == -1):
        return None
    return tree[best].move

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

