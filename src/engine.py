from typing import List, Optional, Tuple

class UltimateTicTacToeEngine:
    def __init__(self):
        # board[box_index][row][col]
        # 0: empty, 1: player 1 (X), 2: player 2 (O)
        self.board = [[[0 for _ in range(3)] for _ in range(3)] for _ in range(9)]
        
        # 記錄 9 個大格的勝負狀態 (0: ongoing, 1: P1 won, 2: P2 won, 3: draw)
        self.big_board = [0 for _ in range(9)]
        
        # 下一手必須下的 box index，None 表示自由落子
        self.active_box: Optional[int] = None 

        self.mapping = {0: '.', 1: 'X', 2: 'O'}

    def __str__(self):
        """簡單的視覺化，方便測試"""
        res = f"Active Box: {self.active_box}\n"
        res += "-" * 19 + "\n"
        for b in range(0, 9, 3):
            for r in range(3):
                res += "| "
                res += " | ".join(["".join(str(self.mapping[self.board[b+i][r][c]]) for c in range(3)) for i in range(3)]) + " |\n"
            res += "-" * 19 + "\n"
        return res

    def check_line_win(self, grid: List[List[int]]) -> int:
        """檢查 3x3 矩陣是否有一方獲勝"""
        # 檢查 row, col
        for i in range(3):
            if grid[i][0] != 0 and grid[i][0] == grid[i][1] == grid[i][2]: return grid[i][0]
            if grid[0][i] != 0 and grid[0][i] == grid[1][i] == grid[2][i]: return grid[0][i]
        # 檢查 diagonal
        if grid[0][0] != 0 and grid[0][0] == grid[1][1] == grid[2][2]: return grid[0][0]
        if grid[0][2] != 0 and grid[0][2] == grid[1][1] == grid[2][0]: return grid[0][2]
        return 0
    
    def check_game_over(self) -> int:
        """檢查整個遊戲是否結束，回傳 0: ongoing, 1: P1 wins, 2: P2 wins, 3: draw"""
        
        # 1. 把 big_board (1D list) 轉換成 3x3 的 2D list
        # self.big_board: [b0, b1, b2, b3, b4, b5, b6, b7, b8]
        big_board_2d = [self.big_board[i:i+3] for i in range(0, 9, 3)]
        
        # 2. 檢查大盤是否有連線獲勝
        winner = self.check_line_win(big_board_2d)
        if winner != 0:
            return winner # 1 或 2
        
        # 3. 檢查是否平手 (所有 big_board 的格子都已分出勝負(1或2)或填滿，且沒人連線)
        # 注意：如果 big_board 還有 0，代表遊戲還沒結束
        if all(status != 0 for status in self.big_board):
            return 3 # 平手
        
        return 0 # 遊戲繼續

    def get_legal_moves(self) -> List[Tuple[int, int, int]]:
        """回傳所有合法的 (box, row, col)"""
        moves = []
        # 如果 active_box 有指定，且該 box 還沒結束，則只能下在那裡
        target_boxes = [self.active_box] if self.active_box is not None and self.big_board[self.active_box] == 0 else [i for i in range(9) if self.big_board[i] == 0]
        
        for b in target_boxes:
            for r in range(3):
                for c in range(3):
                    if self.board[b][r][c] == 0:
                        moves.append((b, r, c))
        return moves

    def make_move(self, box: int, row: int, col: int, player: int) -> bool:
        """執行落子，成功回傳 True"""
        if (box, row, col) not in self.get_legal_moves():
            return False
            
        self.board[box][row][col] = player
        
        # 檢查小格勝負
        winner = self.check_line_win(self.board[box])
        if winner != 0 and self.big_board[box] == 0:
            self.big_board[box] = winner
            
        # 更新 active_box (下一手去那個 box)
        if self.big_board[row * 3 + col] == 0:
            self.active_box = row * 3 + col
        else:
            self.active_box = None # 該格已滿或結束，自由落子
            
        return True

    def to_llm_string(self) -> str:
        """你專用的轉換器：把 3D board 轉成 Prompt 格式"""
        # 這裡你可以隨意修改格式，只要讓 Llama-3 看得懂就好
        res = f"Active_Box: {self.active_box}\n"
        for b in range(9):
            grid = "".join([str(self.board[b][r][c]) for r in range(3) for c in range(3)])
            res += f"Box{b}:{grid} "
        return res