import numpy as np


class UltimateTicTacToeEnv:

    __slots__ = (
        "board",
        "macro_board",
        "active_micro",
        "current_player",
    )

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
            "current_player": self.current_player,
        }

    def clone(self):
        new_env = self.__class__.__new__(self.__class__)
        new_env.board = self.board.copy()
        new_env.macro_board = self.macro_board.copy()
        new_env.active_micro = self.active_micro
        new_env.current_player = self.current_player
        return new_env

    def get_legal_actions(self):
        legal_masks = np.zeros(81, dtype=np.int8)

        active = self.active_micro

        if active == -1 or self.macro_board[active] != 0:
            board = self.board
            macro = self.macro_board

            for m in range(9):
                if macro[m] == 0:
                    start = m * 9
                    sub = board[m]

                    legal_masks[start + 0] = 1 if sub[0, 0] == 0 else 0
                    legal_masks[start + 1] = 1 if sub[0, 1] == 0 else 0
                    legal_masks[start + 2] = 1 if sub[0, 2] == 0 else 0
                    legal_masks[start + 3] = 1 if sub[1, 0] == 0 else 0
                    legal_masks[start + 4] = 1 if sub[1, 1] == 0 else 0
                    legal_masks[start + 5] = 1 if sub[1, 2] == 0 else 0
                    legal_masks[start + 6] = 1 if sub[2, 0] == 0 else 0
                    legal_masks[start + 7] = 1 if sub[2, 1] == 0 else 0
                    legal_masks[start + 8] = 1 if sub[2, 2] == 0 else 0

        else:
            start = active * 9
            sub = self.board[active]

            legal_masks[start + 0] = 1 if sub[0, 0] == 0 else 0
            legal_masks[start + 1] = 1 if sub[0, 1] == 0 else 0
            legal_masks[start + 2] = 1 if sub[0, 2] == 0 else 0
            legal_masks[start + 3] = 1 if sub[1, 0] == 0 else 0
            legal_masks[start + 4] = 1 if sub[1, 1] == 0 else 0
            legal_masks[start + 5] = 1 if sub[1, 2] == 0 else 0
            legal_masks[start + 6] = 1 if sub[2, 0] == 0 else 0
            legal_masks[start + 7] = 1 if sub[2, 1] == 0 else 0
            legal_masks[start + 8] = 1 if sub[2, 2] == 0 else 0

        return legal_masks

    def legal_actions_list(self):
        actions = []
        active = self.active_micro

        if active == -1 or self.macro_board[active] != 0:
            for m in range(9):
                if self.macro_board[m] == 0:
                    base = m * 9
                    sub = self.board[m]
                    if sub[0, 0] == 0: actions.append(base + 0)
                    if sub[0, 1] == 0: actions.append(base + 1)
                    if sub[0, 2] == 0: actions.append(base + 2)
                    if sub[1, 0] == 0: actions.append(base + 3)
                    if sub[1, 1] == 0: actions.append(base + 4)
                    if sub[1, 2] == 0: actions.append(base + 5)
                    if sub[2, 0] == 0: actions.append(base + 6)
                    if sub[2, 1] == 0: actions.append(base + 7)
                    if sub[2, 2] == 0: actions.append(base + 8)
        else:
            base = active * 9
            sub = self.board[active]
            if sub[0, 0] == 0: actions.append(base + 0)
            if sub[0, 1] == 0: actions.append(base + 1)
            if sub[0, 2] == 0: actions.append(base + 2)
            if sub[1, 0] == 0: actions.append(base + 3)
            if sub[1, 1] == 0: actions.append(base + 4)
            if sub[1, 2] == 0: actions.append(base + 5)
            if sub[2, 0] == 0: actions.append(base + 6)
            if sub[2, 1] == 0: actions.append(base + 7)
            if sub[2, 2] == 0: actions.append(base + 8)

        return actions

    def _is_legal_action(self, action):
        if action < 0 or action >= 81:
            return False

        micro_idx = action // 9
        cell_idx = action % 9
        row = cell_idx // 3
        col = cell_idx % 3

        if self.macro_board[micro_idx] != 0:
            return False

        active = self.active_micro
        if active != -1 and self.macro_board[active] == 0 and micro_idx != active:
            return False

        return self.board[micro_idx, row, col] == 0

    def step(self, action):
        action = int(action)

        micro_idx = action // 9
        cell_idx = action % 9
        row = cell_idx // 3
        col = cell_idx % 3

        if not self._is_legal_action(action):
            raise ValueError(f"玩家 {self.current_player} 企圖下在非法位置 {action}！")

        player = self.current_player
        self.board[micro_idx, row, col] = player

        sub = self.board[micro_idx]
        if self._check_3x3_win(sub, player):
            self.macro_board[micro_idx] = player
        elif self._is_micro_full(sub):
            self.macro_board[micro_idx] = 2

        if self.macro_board[cell_idx] != 0:
            self.active_micro = -1
        else:
            self.active_micro = cell_idx

        terminated = False
        reward = 0

        if self._check_3x3_win(self.macro_board, player):
            terminated = True
            reward = 1
        elif self._is_macro_full():
            terminated = True
            reward = 0

        info = {
            "last_player": player,
            "last_action": action,
        }

        self.current_player = -player

        return self._get_obs(), reward, terminated, info

    @staticmethod
    def _is_micro_full(sub):
        return (
            sub[0, 0] != 0 and sub[0, 1] != 0 and sub[0, 2] != 0 and
            sub[1, 0] != 0 and sub[1, 1] != 0 and sub[1, 2] != 0 and
            sub[2, 0] != 0 and sub[2, 1] != 0 and sub[2, 2] != 0
        )

    def _is_macro_full(self):
        m = self.macro_board
        return (
            m[0] != 0 and m[1] != 0 and m[2] != 0 and
            m[3] != 0 and m[4] != 0 and m[5] != 0 and
            m[6] != 0 and m[7] != 0 and m[8] != 0
        )

    def _check_3x3_win(self, board_3x3, player):
        if getattr(board_3x3, "ndim", None) == 1:
            b0 = board_3x3[0]; b1 = board_3x3[1]; b2 = board_3x3[2]
            b3 = board_3x3[3]; b4 = board_3x3[4]; b5 = board_3x3[5]
            b6 = board_3x3[6]; b7 = board_3x3[7]; b8 = board_3x3[8]
        else:
            b0 = board_3x3[0, 0]; b1 = board_3x3[0, 1]; b2 = board_3x3[0, 2]
            b3 = board_3x3[1, 0]; b4 = board_3x3[1, 1]; b5 = board_3x3[1, 2]
            b6 = board_3x3[2, 0]; b7 = board_3x3[2, 1]; b8 = board_3x3[2, 2]

        return (
            (b0 == player and b1 == player and b2 == player) or
            (b3 == player and b4 == player and b5 == player) or
            (b6 == player and b7 == player and b8 == player) or
            (b0 == player and b3 == player and b6 == player) or
            (b1 == player and b4 == player and b7 == player) or
            (b2 == player and b5 == player and b8 == player) or
            (b0 == player and b4 == player and b8 == player) or
            (b2 == player and b4 == player and b6 == player)
        )

    def render(self):
        lines = []
        for macro_row in range(3):
            for micro_row in range(3):
                line_str = ""
                for macro_col in range(3):
                    m_idx = macro_row * 3 + macro_col
                    row_cells = self.board[m_idx, micro_row]
                    chars = [
                        "O" if c == 1 else "X" if c == -1 else "."
                        for c in row_cells
                    ]
                    line_str += " " + " ".join(chars) + " |"
                lines.append(line_str[:-1])
            if macro_row < 2:
                lines.append("-" * 27)

        print("\n".join(lines))
        print(
            f"當前玩家: {'O (1)' if self.current_player == 1 else 'X (-1)'} | "
            f"限制區域 Micro-board: {self.active_micro}"
        )
