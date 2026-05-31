from __future__ import annotations

import math
import time

from .game_state import GameState
from .lines import SMALL_LINES
from .types import EvalConfig, EvalFeatures, Player, SearchStats


def _product(values: list[int]) -> int:
    result = 1
    for value in values:
        result *= value
    return result


def evaluate(state: GameState, model_player: Player, config: EvalConfig, depth_remaining: int, stats: SearchStats | None = None) -> float:
    start = time.perf_counter()
    try:
        if state.game_result is not None:
            if state.game_result == "D":
                return float(config.terminal_draw)
            if state.game_result == model_player:
                return float(config.terminal_win + depth_remaining)
            return float(config.terminal_loss - depth_remaining)

        features = compute_features(state, config)
        x_score = (
            features.x_positional_score
            + features.x_local_board_score
            + features.x_small_board_owned_score
            + features.x_global_line_score
        )
        o_score = (
            features.o_positional_score
            + features.o_local_board_score
            + features.o_small_board_owned_score
            + features.o_global_line_score
        )
        score = x_score - o_score if model_player == "X" else o_score - x_score
        if state.current_turn == model_player:
            score += features.send_penalty
        else:
            score -= features.send_penalty
        return float(score)
    finally:
        if stats is not None:
            stats.heuristic_time_sec += time.perf_counter() - start


def compute_features(state: GameState, config: EvalConfig) -> EvalFeatures:
    features = EvalFeatures()
    small_owned_value = sum(config.small_cell_weights)

    for board in range(9):
        board_weight = config.big_board_weights[board]
        status = state.small_board_status[board]
        if status == "X":
            features.x_small_board_owned_score += small_owned_value * board_weight
        elif status == "O":
            features.o_small_board_owned_score += small_owned_value * board_weight

        for cell in range(9):
            bit = 1 << (board * 9 + cell)
            value = board_weight * config.small_cell_weights[cell]
            if state.x_bits & bit:
                features.x_positional_score += value
            elif state.o_bits & bit:
                features.o_positional_score += value

        if status is None:
            x_local, o_local = _local_line_scores(state, board, config)
            features.x_local_board_score += x_local * board_weight
            features.o_local_board_score += o_local * board_weight

    x_global, o_global = _global_line_scores(state, config)
    features.x_global_line_score = x_global
    features.o_global_line_score = o_global
    features.send_penalty = _send_penalty(state, config)
    return features


def _local_line_scores(state: GameState, board: int, config: EvalConfig) -> tuple[float, float]:
    x_total = 0.0
    o_total = 0.0
    board_offset = board * 9
    for line in SMALL_LINES:
        x_cells = []
        o_cells = []
        for cell in line:
            bit = 1 << (board_offset + cell)
            if state.x_bits & bit:
                x_cells.append(cell)
            elif state.o_bits & bit:
                o_cells.append(cell)
        if x_cells and not o_cells:
            x_total += _product([config.small_cell_weights[cell] for cell in x_cells])
        elif o_cells and not x_cells:
            o_total += _product([config.small_cell_weights[cell] for cell in o_cells])
    return x_total, o_total


def _global_line_scores(state: GameState, config: EvalConfig) -> tuple[float, float]:
    x_total = 0.0
    o_total = 0.0
    for line in SMALL_LINES:
        statuses = [state.small_board_status[board] for board in line]
        if "D" in statuses or ("X" in statuses and "O" in statuses):
            continue
        if "X" in statuses:
            x_total += _product([config.big_board_weights[board] for board in line if state.small_board_status[board] == "X"])
        elif "O" in statuses:
            o_total += _product([config.big_board_weights[board] for board in line if state.small_board_status[board] == "O"])
    return x_total, o_total


def _send_penalty(state: GameState, config: EvalConfig) -> float:
    boards = [board for board in range(9) if state.legal_board_mask & (1 << board)]
    if not boards:
        return 0.0
    raw = _product([config.big_board_weights[board] for board in boards])
    if config.send_penalty_mode == "log":
        return sum(config.small_cell_weights) * math.log(raw)
    return config.big_board_weights[4] * math.sqrt(raw)
