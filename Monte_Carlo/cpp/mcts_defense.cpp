#include <bits/stdc++.h>
using namespace std;
auto rnd = mt19937(time(NULL));
#define pii pair<int,int>
#define F first
#define S second
#define pb push_back
#define all(x) (x).begin(),(x).end()
#define Ststone ios_base::sync_with_stdio(0);cin.tie(0)
const int ST = 50000;
const double MCTS_C = 2;
const double DRAW_SCORE = 0.8;
const int ROLLOUT_TYPE = 2;
const int FINAL_TYPE = 0;

struct board{
    int big[9];
    int state[9][9];
    bool can_place[9][9];
    int nxt = 1;
    void init(){
        for(int i=0;i<9;i++){
            for(int j=0;j<9;j++){
                can_place[i][j] = 1;
                state[i][j] = 0;
            }
            big[i] = 0;
        }
    }
    int check_win(){
        if(big[0] == big[1] && big[1] == big[2] && big[0] > 0) return big[0];
        if(big[3] == big[4] && big[4] == big[5] && big[3] > 0) return big[3];
        if(big[6] == big[7] && big[7] == big[8] && big[6] > 0) return big[6];
        if(big[0] == big[3] && big[3] == big[6] && big[0] > 0) return big[0];
        if(big[1] == big[4] && big[4] == big[7] && big[1] > 0) return big[1];
        if(big[2] == big[5] && big[5] == big[8] && big[2] > 0) return big[2];
        if(big[0] == big[4] && big[4] == big[8] && big[0] > 0) return big[0];
        if(big[2] == big[4] && big[4] == big[6] && big[2] > 0) return big[2];
        int cnt = 0;
        for(int i=0;i<9;i++){
            if(big[i] != 0) cnt++;
        }
        if(cnt == 9) return -1;
        return 0;
    }
    void update(int chunk,int idx){
        bool finish = 0;
        for(int i=0;i<9;i++){
            for(int j=0;j<9;j++){
                can_place[i][j] = 0;
            }
        }
        if(state[chunk][0] == state[chunk][1] && state[chunk][1] == state[chunk][2] && state[chunk][0] != 0) finish = 1;
        if(state[chunk][3] == state[chunk][4] && state[chunk][4] == state[chunk][5] && state[chunk][3] != 0) finish = 1;
        if(state[chunk][6] == state[chunk][7] && state[chunk][7] == state[chunk][8] && state[chunk][6] != 0) finish = 1;
        if(state[chunk][0] == state[chunk][3] && state[chunk][3] == state[chunk][6] && state[chunk][0] != 0) finish = 1;
        if(state[chunk][1] == state[chunk][4] && state[chunk][4] == state[chunk][7] && state[chunk][1] != 0) finish = 1;
        if(state[chunk][2] == state[chunk][5] && state[chunk][5] == state[chunk][8] && state[chunk][2] != 0) finish = 1;
        if(state[chunk][0] == state[chunk][4] && state[chunk][4] == state[chunk][8] && state[chunk][0] != 0) finish = 1;
        if(state[chunk][2] == state[chunk][4] && state[chunk][4] == state[chunk][6] && state[chunk][2] != 0) finish = 1;
        if(finish){
            big[chunk] = nxt;
        }
        int cnt_small = 0;
        for(int i=0;i<9;i++){
            if(state[chunk][i] != 0) cnt_small++;
        }
        if(big[chunk] == 0 && cnt_small == 9) big[chunk] = -1;
        if(big[idx] != 0){
            for(int i=0;i<9;i++){
                if(big[i] != 0) continue;
                for(int j=0;j<9;j++){
                    if(state[i][j] == 0) can_place[i][j] = 1;
                }
            }
        }
        else{
            for(int i=0;i<9;i++){
                if(state[idx][i] == 0) can_place[idx][i] = 1;
            }
        }
    }
    void place(int x,int y){
        if(!can_place[x][y]) return;
        state[x][y] = nxt;
        update(x,y);
        nxt ^= 3;
    }
    void print(){
        cout << "  012 345 678 \n";
        cout << "  --- --- --- \n";
        for(int l=0;l<3;l++){
            for(int i=0;i<3;i++){
                cout << l*3+i << "|";
                for(int j=0;j<3;j++){
                    for(int k=0;k<3;k++){
                        if(state[l*3+j][i*3+k] == 1) cout << 'O';
                        else if(state[l*3+j][i*3+k] == 2) cout << 'X';
                        else cout << ' ';
                    }
                    cout << "|";
                }
                cout << "\n";
            }
            cout << "  --- --- --- \n";
        }
        cout.flush();
    }
};

vector<pii> get_moves(board ret){
    vector<pii> v;
    if(ret.check_win() != 0) return v;
    for(int i=0;i<9;i++){
        for(int j=0;j<9;j++){
            if(ret.can_place[i][j]) v.pb({i,j});
        }
    }
    return v;
}

int cell_weight(int x){
    if(ROLLOUT_TYPE == 0) return 1;
    if(ROLLOUT_TYPE == 1){
        if(x == 4) return 8;
        if(x == 0 || x == 2 || x == 6 || x == 8) return 4;
        return 1;
    }
    if(x == 4) return 5;
    if(x == 1 || x == 3 || x == 5 || x == 7) return 3;
    return 2;
}

pii get_random_move(vector<pii> v){
    int sum = 0;
    for(pii p:v){
        sum += cell_weight(p.S);
    }
    int x = rnd() % sum;
    for(pii p:v){
        x -= cell_weight(p.S);
        if(x < 0) return p;
    }
    return v.back();
}

int simulation(board ret){
    while(ret.check_win() == 0){
        vector<pii> v = get_moves(ret);
        if(v.size() == 0){
            break;
        }
        pii move = get_random_move(v);
        ret.place(move.F,move.S);
    }
    return ret.check_win();
}

double get_score(int res,int player){
    if(res == player) return 1;
    if(res == -1) return DRAW_SCORE;
    return 0;
}

struct node{
    board b;
    pii move = {-1,-1};
    int parent = -1;
    int visit = 0;
    double win = 0;
    vector<int> child;
    vector<pii> untry;
};

int select_child(vector<node> &tree,int u){
    int best = -1;
    double best_val = -1e100;
    const double C = MCTS_C;
    for(int v:tree[u].child){
        if(tree[v].visit == 0) return v;
        double avg = tree[v].win / tree[v].visit;
        double val = avg + C * sqrt(log((double)tree[u].visit + 1) / tree[v].visit);
        if(val > best_val){
            best_val = val;
            best = v;
        }
    }
    return best;
}

board find_bset_move(board ret){
    vector<node> tree;
    node root;
    root.b = ret;
    root.untry = get_moves(ret);
    tree.pb(root);
    for(int t=0;t<ST;t++){
        int u = 0;
        while(tree[u].untry.size() == 0 && tree[u].child.size() > 0){
            u = select_child(tree,u);
        }
        if(tree[u].b.check_win() == 0 && tree[u].untry.size() > 0){
            int idx = rnd() % tree[u].untry.size();
            pii move = tree[u].untry[idx];
            swap(tree[u].untry[idx],tree[u].untry.back());
            tree[u].untry.pop_back();
            board nxt_board = tree[u].b;
            nxt_board.place(move.F,move.S);
            node nxt_node;
            nxt_node.b = nxt_board;
            nxt_node.move = move;
            nxt_node.parent = u;
            nxt_node.untry = get_moves(nxt_board);
            tree.pb(nxt_node);
            tree[u].child.pb((int)tree.size()-1);
            u = (int)tree.size()-1;
        }
        int res = simulation(tree[u].b);
        while(u != -1){
            tree[u].visit++;
            if(tree[u].move.F != -1){
                int player = tree[u].b.nxt ^ 3;
                tree[u].win += get_score(res,player);
            }
            u = tree[u].parent;
        }
    }
    int best = -1;
    for(int v:tree[0].child){
        if(best == -1){
            best = v;
        }
        else if(FINAL_TYPE == 0){
            if(tree[v].visit > tree[best].visit) best = v;
        }
        else{
            double a = tree[v].win / max(1,tree[v].visit);
            double b = tree[best].win / max(1,tree[best].visit);
            if(a > b || (a == b && tree[v].visit > tree[best].visit)) best = v;
        }
    }
    if(best != -1){
        ret.place(tree[best].move.F,tree[best].move.S);
        int x = tree[best].move.F;
        int y = tree[best].move.S;
        cout <<  x/3*3+y/3 << ' ' << x%3*3+y%3 << '\n';
    }
    return ret;
}

int main(){
    Ststone;
    board game;
    game.init();
    int player;
    cin >> player;
    // 0 first
    // 1 second
    int turn = 0;
    // game.print();
    while(game.check_win() == 0){
        if(turn == player){
            // cout << "player's turn\n";
            cout.flush();
            int row,col,x,y;
            cin >> row >> col;
            while(1){
                if(row >= 0 && row < 9 && col >= 0 && col < 9){
                    x = row/3*3+col/3;
                    y = row%3*3+col%3;
                    if(game.can_place[x][y]) break;
                }
                // cout << "invalid input\n";
                cout.flush();
                cin >> row >> col;
            }
            game.place(x,y);
        }
        else{
            // cout << "computer's turn\n";
            cout.flush();
            game = find_bset_move(game);
        }
        turn ^= 1;
        // game.print();
    }
}
