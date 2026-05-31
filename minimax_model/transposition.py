from __future__ import annotations

from dataclasses import dataclass
from .game_state import GameState
from .types import Move


@dataclass(slots=True)
class TTEntry:
    depth: int
    score: float
    best_move: Move | None


class TranspositionTable:
    def __init__(self) -> None:
        self._table: dict[tuple[int, int, str, int], TTEntry] = {}

    def key(self, state: GameState) -> tuple[int, int, str, int]:
        return (state.x_bits, state.o_bits, state.current_turn, state.legal_board_mask)

    def get(self, state: GameState) -> TTEntry | None:
        return self._table.get(self.key(state))

    def store(self, state: GameState, entry: TTEntry) -> None:
        key = self.key(state)
        old = self._table.get(key)
        if old is None or entry.depth >= old.depth:
            self._table[key] = entry
