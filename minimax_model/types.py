from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional, TypedDict

Player = Literal["X", "O"]
GameResult = Optional[Literal["X", "O", "D"]]


class Move(TypedDict):
    board: int
    row: int
    col: int


class LastMove(Move):
    player: Player


@dataclass(slots=True)
class ValidationResult:
    ok: bool
    code: str = ""
    message: str = ""


@dataclass(slots=True)
class EvalConfig:
    terminal_win: int
    terminal_loss: int
    terminal_draw: int
    send_penalty_mode: Literal["log", "sqrt"]
    big_board_weights: list[int]
    small_cell_weights: list[int]


@dataclass(slots=True)
class MoveOrderingConfig:
    tt_best_move: int
    win_global_board: int
    block_global_win: int
    win_small_board: int
    block_small_board: int


@dataclass(slots=True)
class SearchStats:
    thinking_time_sec: float = 0.0
    heuristic_time_sec: float = 0.0
    move_ordering_time_sec: float = 0.0
    search_depth: int = 0
    nodes_searched: int = 0
    alpha_beta_cutoffs: int = 0
    transposition_hits: int = 0


@dataclass(slots=True)
class EvalFeatures:
    x_positional_score: float = 0.0
    o_positional_score: float = 0.0
    x_local_board_score: float = 0.0
    o_local_board_score: float = 0.0
    x_small_board_owned_score: float = 0.0
    o_small_board_owned_score: float = 0.0
    x_global_line_score: float = 0.0
    o_global_line_score: float = 0.0
    send_penalty: float = 0.0


@dataclass(slots=True)
class LineState:
    x_count: int = 0
    o_count: int = 0
    blocked_count: int = 0


def default_eval_config() -> EvalConfig:
    return EvalConfig(
        terminal_win=1_000_000,
        terminal_loss=-1_000_000,
        terminal_draw=0,
        send_penalty_mode="log",
        big_board_weights=[5, 4, 5, 4, 6, 4, 5, 4, 5],
        small_cell_weights=[4, 3, 4, 3, 5, 3, 4, 3, 4],
    )


def default_move_ordering_config() -> MoveOrderingConfig:
    return MoveOrderingConfig(
        tt_best_move=100_000,
        win_global_board=90_000,
        block_global_win=80_000,
        win_small_board=5_000,
        block_small_board=4_000,
    )
