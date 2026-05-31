from __future__ import annotations

from .types import Player


def opponent(player: Player) -> Player:
    return "O" if player == "X" else "X"


def cell_index(board: int, row: int, col: int) -> int:
    return board * 9 + row * 3 + col


def local_cell(row: int, col: int) -> int:
    return row * 3 + col


def bit_for_move(board: int, row: int, col: int) -> int:
    return 1 << cell_index(board, row, col)


def small_board_mask(bits: int, board: int) -> int:
    return (bits >> (board * 9)) & 0b111111111


def is_cell_empty(x_bits: int, o_bits: int, board: int, row: int, col: int) -> bool:
    return ((x_bits | o_bits) & bit_for_move(board, row, col)) == 0


def cell_owner(x_bits: int, o_bits: int, board: int, row: int, col: int) -> Player | None:
    bit = bit_for_move(board, row, col)
    if x_bits & bit:
        return "X"
    if o_bits & bit:
        return "O"
    return None


def set_cell(bits: int, board: int, row: int, col: int) -> int:
    return bits | bit_for_move(board, row, col)


def visual_board_to_bitboards(visual_board: list) -> tuple[int, int]:
    if not isinstance(visual_board, list) or len(visual_board) != 3:
        raise ValueError("board must be a 3x3 list of small boards.")
    x_bits = 0
    o_bits = 0
    for big_row in range(3):
        if not isinstance(visual_board[big_row], list) or len(visual_board[big_row]) != 3:
            raise ValueError("board must be a 3x3 list of small boards.")
        for big_col in range(3):
            board = big_row * 3 + big_col
            small = visual_board[big_row][big_col]
            if not isinstance(small, list) or len(small) != 3:
                raise ValueError("each small board must be a 3x3 list.")
            for row in range(3):
                if not isinstance(small[row], list) or len(small[row]) != 3:
                    raise ValueError("each small board row must contain 3 cells.")
                for col in range(3):
                    value = small[row][col]
                    if value == "X":
                        x_bits = set_cell(x_bits, board, row, col)
                    elif value == "O":
                        o_bits = set_cell(o_bits, board, row, col)
                    elif value is not None:
                        raise ValueError('cell values must be "X", "O", or None.')
    if x_bits & o_bits:
        raise ValueError("a cell cannot belong to both players.")
    return x_bits, o_bits


def bitboards_to_visual_board(x_bits: int, o_bits: int) -> list:
    visual = []
    for big_row in range(3):
        board_row = []
        for big_col in range(3):
            board = big_row * 3 + big_col
            small = []
            for row in range(3):
                cells = []
                for col in range(3):
                    owner = cell_owner(x_bits, o_bits, board, row, col)
                    cells.append(owner)
                small.append(cells)
            board_row.append(small)
        visual.append(board_row)
    return visual


def count_moves(x_bits: int, o_bits: int) -> int:
    return x_bits.bit_count() + o_bits.bit_count()


def count_by_player(x_bits: int, o_bits: int) -> tuple[int, int]:
    return x_bits.bit_count(), o_bits.bit_count()
