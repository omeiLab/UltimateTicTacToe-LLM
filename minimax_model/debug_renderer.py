from __future__ import annotations

from pathlib import Path

from .bitboard import cell_owner
from .game_state import GameState, generate_legal_moves, total_moves
from .types import Move, SearchStats


def append_debug_report(
    path: str,
    state: GameState,
    model_player: str,
    starting_player: str,
    opponent_player: str,
    status: str,
    move: Move | None,
    stats: SearchStats,
) -> None:
    report = render_debug_report(state, model_player, starting_player, opponent_player, status, move, stats)
    output_path = Path(path)
    if output_path.parent != Path("."):
        output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as handle:
        handle.write(report)
        handle.write("\n")


def render_debug_report(
    state: GameState,
    model_player: str,
    starting_player: str,
    opponent_player: str,
    status: str,
    move: Move | None,
    stats: SearchStats,
) -> str:
    legal_boards = [idx for idx in range(9) if state.legal_board_mask & (1 << idx)]
    return "\n".join(
        [
            "=== M Debug Report ===",
            "",
            f"Status: {status}",
            f"Model player: {model_player}",
            f"Starting player: {starting_player}",
            f"Opponent player: {opponent_player}",
            f"Current turn: {state.current_turn}",
            f"Last model move: {move}",
            f"Legal boards: {legal_boards}",
            f"Legal move count: {len(generate_legal_moves(state))}",
            f"Move count: {total_moves(state)}",
            f"Game result: {state.game_result}",
            f"Small board status: {state.small_board_status}",
            "",
            "=== Search Stats ===",
            "",
            f"Thinking time: {stats.thinking_time_sec:.6f} sec",
            f"Heuristic time: {stats.heuristic_time_sec:.6f} sec",
            f"Move ordering time: {stats.move_ordering_time_sec:.6f} sec",
            f"Search depth: {stats.search_depth}",
            "",
            "=== Tuning Stats ===",
            "",
            f"Nodes searched: {stats.nodes_searched}",
            f"Alpha-beta cutoffs: {stats.alpha_beta_cutoffs}",
            f"Transposition hits: {stats.transposition_hits}",
            "",
            "=== Board ===",
            "",
            render_board(state),
            "",
        ]
    )


def render_board(state: GameState) -> str:
    rows = []
    for big_row in range(3):
        for row in range(3):
            parts = []
            for big_col in range(3):
                board = big_row * 3 + big_col
                cells = []
                for col in range(3):
                    cells.append(cell_owner(state.x_bits, state.o_bits, board, row, col) or ".")
                parts.append(" ".join(cells))
            rows.append(" | ".join(parts))
        if big_row < 2:
            rows.append("------+-------+------")
    return "\n".join(rows)
