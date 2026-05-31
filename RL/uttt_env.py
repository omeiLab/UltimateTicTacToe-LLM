import numpy as np

class UltimateTicTacToeEnv:
    def __init__(self):
        self.reset()
        
    def reset(self):
        self.board = np.zeros((9, 3, 3), dtype=np.int8)
        
        self.macro_board = np.zeros(9, dtype=np.int8)
        
        self.active_micro = -1 
        
        self.current_player = 1
        
        return self._get_obs()
        
    def _get_obs(self):
        return {
            "board": self.board.copy(),
            "macro_board": self.macro_board.copy(),
            "active_micro": self.active_micro,
            "current_player": self.current_player
        }
        
    def get_legal_actions(self):
        legal_masks = np.zeros(81, dtype=np.int8)
        
        if self.active_micro == -1 or self.macro_board[self.active_micro] != 0:
            for m in range(9):
                if self.macro_board[m] == 0:
                    sub_board = self.board[m].flatten()
                    legal_masks[m*9 : (m+1)*9] = (sub_board == 0)
        else:
            sub_board = self.board[self.active_micro].flatten()
            legal_masks[self.active_micro*9 : (self.active_micro+1)*9] = (sub_board == 0)
            
        return legal_masks

    def step(self, action):
        micro_idx = action // 9
        cell_idx = action % 9
        row, col = cell_idx // 3, cell_idx % 3
        
        legal_actions = self.get_legal_actions()
        if legal_actions[action] == 0:
            raise ValueError(f"玩家 {self.current_player} 企圖下在非法位置 {action}！")
        
        self.board[micro_idx, row, col] = self.current_player
        
        if self._check_3x3_win(self.board[micro_idx], self.current_player):
            self.macro_board[micro_idx] = self.current_player
        elif np.all(self.board[micro_idx] != 0):
            self.macro_board[micro_idx] = 2
            
        next_micro = cell_idx 
        
        if self.macro_board[next_micro] != 0:
            self.active_micro = -1
        else:
            self.active_micro = next_micro
            
        terminated = False
        reward = 0
        
        if self._check_3x3_win(self.macro_board, self.current_player):
            terminated = True
            reward = 1
        elif np.all(self.macro_board != 0):
            terminated = True
            reward = 0
            
        info = {"last_player": self.current_player, "last_action": action}
        
        self.current_player = -self.current_player
        
        return self._get_obs(), reward, terminated, info
        
    def _check_3x3_win(self, board_3x3, player):
        if board_3x3.ndim == 1:
            b = board_3x3.reshape(3, 3)
        else:
            b = board_3x3

        for i in range(3):
            if np.all(b[i, :] == player) or np.all(b[:, i] == player):
                return True
        if b[0, 0] == player and b[1, 1] == player and b[2, 2] == player:
            return True
        if b[0, 2] == player and b[1, 1] == player and b[2, 0] == player:
            return True
            
        return False

    def render(self):
        lines = []
        for macro_row in range(3):
            for micro_row in range(3):
                line_str = ""
                for macro_col in range(3):
                    m_idx = macro_row * 3 + macro_col
                    row_cells = self.board[m_idx, micro_row]
                    chars = [ 'O' if c == 1 else 'X' if c == -1 else '.' for c in row_cells ]
                    line_str += " " + " ".join(chars) + " |"
                lines.append(line_str[:-1])
            if macro_row < 2:
                lines.append("-" * 27)
        print("\n".join(lines))
        print(f"當前玩家: {'O (1)' if self.current_player == 1 else 'X (-1)'} | 限制區域 Micro-board: {self.active_micro}")