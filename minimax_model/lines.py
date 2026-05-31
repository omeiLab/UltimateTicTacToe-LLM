from __future__ import annotations

SMALL_LINES: tuple[tuple[int, int, int], ...] = (
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
)

WIN_MASKS: tuple[int, ...] = tuple(sum(1 << cell for cell in line) for line in SMALL_LINES)

CELL_TO_SMALL_LINES: dict[int, list[int]] = {
    0: [0, 3, 6],
    1: [0, 4],
    2: [0, 5, 7],
    3: [1, 3],
    4: [1, 4, 6, 7],
    5: [1, 5],
    6: [2, 3, 7],
    7: [2, 4],
    8: [2, 5, 6],
}

BOARD_TO_GLOBAL_LINES = CELL_TO_SMALL_LINES
ALL_BOARDS_MASK = (1 << 9) - 1
