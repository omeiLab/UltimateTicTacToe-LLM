#include <bits/stdc++.h>
using namespace std;
auto rnd = mt19937(time(NULL));
#define pii pair<int,int>
#define F first
#define S second
#define pb push_back
#define all(x) (x).begin(),(x).end()
#define Ststone ios_base::sync_with_stdio(0);cin.tie(0)
const int ST = 1000;

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

int simulation(board ret){
    while(ret.check_win() == 0){
        vector<pii> v;
        for(int i=0;i<9;i++){
            for(int j=0;j<9;j++){
                if(ret.can_place[i][j]) v.push_back({i,j});
            }
        }
        if(v.size() == 0){
            break;
        }
        int idx = rnd() % v.size();
        ret.place(v[idx].F,v[idx].S);
    }
    return ret.check_win();
}

board find_bset_move(board ret){
    vector<pair<int,pii>> rank;
    for(int i=0;i<9;i++){
        for(int j=0;j<9;j++){
            if(ret.can_place[i][j]){
                board now = ret;
                int player = now.nxt;
                now.place(i,j);
                int cnt = 1;
                for(int t=0;t<ST;t++){
                    int res = simulation(now);
                    if(res == player) cnt += 2;
                    else if(res == -1) cnt++;
                    else cnt -= 10;
                }
                rank.pb({cnt,{i,j}});
            }
        }
    }
    sort(all(rank));
    ret.place(rank.back().S.F,rank.back().S.S);
    int x = rank.back().S.F;
    int y = rank.back().S.S;
    cout <<  x/3*3+y/3 << ' ' << x%3*3+y%3 << '\n';
    return ret;
}

int main(){
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