from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .bitboard import opponent
from .debug_renderer import append_debug_report
from .exceptions import InvalidInitialStateError
from .game_state import (
    GameState,
    debug_validate_model_move,
    generate_legal_moves,
    validate_opponent_move,
)
from .search import SearchEngine
from .transposition import TranspositionTable
from .types import Move, Player, SearchStats, default_eval_config, default_move_ordering_config


class MinimaxAgent:
    def __init__(
        self,
        model_player: Player = "X",
        starting_player: Player = "X",
        initial_board: dict | None = None,
        debug: bool = False,
        debug_output_path: str = "debug_board.txt",
        max_depth: int = 80,
        time_limit_sec: float = 3.0,
    ) -> None:
        if model_player not in ("X", "O"):
            raise InvalidInitialStateError('model_player must be "X" or "O".')
        if starting_player not in ("X", "O"):
            raise InvalidInitialStateError('starting_player must be "X" or "O".')
        if not isinstance(max_depth, int) or max_depth <= 0:
            raise InvalidInitialStateError("max_depth must be a positive integer.")
        if not isinstance(time_limit_sec, (int, float)) or time_limit_sec <= 0:
            raise InvalidInitialStateError("time_limit_sec must be positive.")

        self.model_player: Player = model_player
        self.opponent_player: Player = opponent(model_player)
        self.starting_player: Player = starting_player
        self.debug = debug
        self.debug_output_path = debug_output_path
        self.max_depth = max_depth
        self.time_limit_sec = float(time_limit_sec)
        self.eval_config = default_eval_config()
        self.move_ordering_config = default_move_ordering_config()
        self.transposition_table = TranspositionTable()
        if self.debug:
            try:
                self._reset_debug_output()
            except OSError as exc:
                raise InvalidInitialStateError("debug_output_path cannot be initialized in debug mode.") from exc

        try:
            self.state = (
                GameState.new(starting_player)
                if initial_board is None
                else GameState.from_initial_board(initial_board, starting_player)
            )
        except ValueError as exc:
            raise InvalidInitialStateError(str(exc)) from exc

    def step(self, move: Move | None = None) -> dict[str, Any]:
        zero_stats = SearchStats()
        if move is None:
            if self.state.game_result is not None:
                return self._return_with_debug(self._game_over_result(zero_stats, None), None, zero_stats)
            if self.state.current_turn != self.model_player:
                return self._return_with_debug(
                    {
                        "status": "invalid_state",
                        "move": None,
                        "error": {
                            "code": "NOT_MODEL_TURN",
                            "message": "It is not model player's turn.",
                        },
                    },
                    None,
                    zero_stats,
                )
        else:
            validation = validate_opponent_move(self.state, move, self.opponent_player)
            if not validation.ok:
                return self._return_with_debug(
                    {
                        "status": "invalid_move",
                        "move": None,
                        "error": {
                            "code": validation.code or "ILLEGAL_MOVE",
                            "message": validation.message or "Move is not legal in the current state.",
                        },
                    },
                    None,
                    zero_stats,
                )
            self.state.apply_move(move, self.opponent_player)
            if self.state.game_result is not None:
                return self._return_with_debug(self._game_over_result(zero_stats, None), None, zero_stats)

        legal_moves = generate_legal_moves(self.state)
        if not legal_moves:
            self.state.game_result = "D"
            return self._return_with_debug(self._game_over_result(zero_stats, None), None, zero_stats)

        engine = SearchEngine(
            model_player=self.model_player,
            eval_config=self.eval_config,
            move_ordering_config=self.move_ordering_config,
            transposition_table=self.transposition_table,
            max_depth=self.max_depth,
            time_limit_sec=self.time_limit_sec,
        )
        best_move, stats = engine.search(self.state)
        if best_move is None:
            self.state.game_result = "D"
            return self._return_with_debug(self._game_over_result(stats, None), None, stats)

        if self.debug:
            validation = debug_validate_model_move(self.state, best_move, self.model_player)
            if not validation.ok:
                return self._return_with_debug(
                    {
                        "status": "internal_error",
                        "move": None,
                        "error": {
                            "code": "MODEL_MOVE_ILLEGAL",
                            "message": "Model selected an illegal move.",
                        },
                    },
                    best_move,
                    stats,
                )

        self.state.apply_move(best_move, self.model_player)
        result = {
            "status": "ok",
            "move": best_move,
            "player": self.model_player,
            "stats": self._stats_dict(stats),
        }
        if self.state.game_result is not None:
            result = self._game_over_result(stats, best_move)
        return self._return_with_debug(result, best_move, stats)

    def _return_with_debug(self, result: dict[str, Any], move: Move | None, stats: SearchStats) -> dict[str, Any]:
        if not self.debug:
            return result
        try:
            append_debug_report(
                self.debug_output_path,
                self.state,
                self.model_player,
                self.starting_player,
                self.opponent_player,
                result["status"],
                move,
                stats,
            )
        except OSError:
            return {
                "status": "internal_error",
                "move": None,
                "error": {
                    "code": "DEBUG_WRITE_FAILED",
                    "message": "Failed to write debug report.",
                },
            }
        return result

    def _game_over_result(self, stats: SearchStats, move: Move | None) -> dict[str, Any]:
        return {
            "status": "game_over",
            "move": move,
            "winner": self.state.game_result,
            "player": self.model_player,
            "stats": self._stats_dict(stats),
        }

    @staticmethod
    def _stats_dict(stats: SearchStats) -> dict[str, float]:
        return {
            "thinking_time_sec": stats.thinking_time_sec,
        }

    @staticmethod
    def format_result(result: dict[str, Any]) -> str:
        return json.dumps(result, indent=4, ensure_ascii=False)

    def _reset_debug_output(self) -> None:
        output_path = Path(self.debug_output_path)
        if output_path.parent != Path("."):
            output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("", encoding="utf-8")
