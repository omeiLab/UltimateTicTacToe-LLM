from __future__ import annotations

import time

from .bitboard import local_cell, opponent
from .game_state import (
    GameState,
    move_blocks_global_win,
    move_wins_game_by_small_board,
    move_wins_small_board,
    player_has_two_line_threat,
)
from .types import Move, MoveOrderingConfig, SearchStats


def order_moves(
    state: GameState,
    moves: list[Move],
    config: MoveOrderingConfig,
    tt_best_move: Move | None = None,
    stats: SearchStats | None = None,
) -> list[Move]:
    start = time.perf_counter()
    try:
        scored = [(score_move(state, move, config, tt_best_move), idx, move) for idx, move in enumerate(moves)]
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [move for _, _, move in scored]
    finally:
        if stats is not None:
            stats.move_ordering_time_sec += time.perf_counter() - start


def score_move(state: GameState, move: Move, config: MoveOrderingConfig, tt_best_move: Move | None) -> int:
    score = 0
    player = state.current_turn
    if tt_best_move == move:
        score += config.tt_best_move
    if move_wins_game_by_small_board(state, move, player):
        score += config.win_global_board
    if move_blocks_global_win(state, move, player):
        score += config.block_global_win
    if move_wins_small_board(state, move, player):
        score += config.win_small_board
    if player_has_two_line_threat(state, move["board"], local_cell(move["row"], move["col"]), opponent(player)):
        score += config.block_small_board
    return score
