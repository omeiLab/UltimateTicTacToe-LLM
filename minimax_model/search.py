from __future__ import annotations

import math
import time

from .game_state import GameState, generate_legal_moves
from .heuristic import evaluate
from .move_ordering import order_moves
from .transposition import TTEntry, TranspositionTable
from .types import EvalConfig, Move, MoveOrderingConfig, Player, SearchStats


class SearchTimeout(Exception):
    pass


class SearchEngine:
    def __init__(
        self,
        model_player: Player,
        eval_config: EvalConfig,
        move_ordering_config: MoveOrderingConfig,
        transposition_table: TranspositionTable,
        max_depth: int,
        time_limit_sec: float,
    ) -> None:
        self.model_player = model_player
        self.eval_config = eval_config
        self.move_ordering_config = move_ordering_config
        self.tt = transposition_table
        self.max_depth = max_depth
        self.time_limit_sec = time_limit_sec
        self.deadline = 0.0
        self.stats = SearchStats()

    def search(self, state: GameState) -> tuple[Move | None, SearchStats]:
        self.deadline = time.perf_counter() + self.time_limit_sec
        self.stats = SearchStats()
        thinking_start = time.perf_counter()
        root_moves = generate_legal_moves(state)
        if not root_moves:
            self.stats.thinking_time_sec = time.perf_counter() - thinking_start
            return None, self.stats

        tt_best = self.tt.get(state).best_move if self.tt.get(state) else None
        fallback_moves = order_moves(state, root_moves, self.move_ordering_config, tt_best, self.stats)
        best_move = fallback_moves[0]
        completed_any_depth = False

        try:
            for depth in range(1, self.max_depth + 1):
                self._check_timeout()
                move, _ = self._search_root(state, depth)
                if move is not None:
                    best_move = move
                    completed_any_depth = True
                    self.stats.search_depth = depth
        except SearchTimeout:
            pass

        if not completed_any_depth:
            best_move = fallback_moves[0]
        self.stats.thinking_time_sec = time.perf_counter() - thinking_start
        return best_move, self.stats

    def _search_root(self, state: GameState, depth: int) -> tuple[Move | None, float]:
        alpha = -math.inf
        beta = math.inf
        best_move: Move | None = None
        best_score = -math.inf
        tt_best = self.tt.get(state).best_move if self.tt.get(state) else None
        moves = order_moves(state, generate_legal_moves(state), self.move_ordering_config, tt_best, self.stats)
        for move in moves:
            self._check_timeout()
            delta = state.apply_move(move)
            try:
                score = self._minimax(state, depth - 1, alpha, beta)
            finally:
                state.undo_move(delta)
            if score > best_score:
                best_score = score
                best_move = move
            alpha = max(alpha, best_score)
        self.tt.store(state, TTEntry(depth=depth, score=best_score, best_move=best_move))
        return best_move, best_score

    def _minimax(self, state: GameState, depth: int, alpha: float, beta: float) -> float:
        self._check_timeout()
        self.stats.nodes_searched += 1
        if state.game_result is not None or depth == 0:
            return evaluate(state, self.model_player, self.eval_config, depth, self.stats)

        entry = self.tt.get(state)
        if entry is not None and entry.depth >= depth:
            self.stats.transposition_hits += 1
            return entry.score

        moves = generate_legal_moves(state)
        if not moves:
            state.game_result = "D"
            score = evaluate(state, self.model_player, self.eval_config, depth, self.stats)
            state.game_result = None
            return score

        tt_best = entry.best_move if entry else None
        moves = order_moves(state, moves, self.move_ordering_config, tt_best, self.stats)
        maximizing = state.current_turn == self.model_player
        best_move: Move | None = None

        if maximizing:
            value = -math.inf
            for move in moves:
                delta = state.apply_move(move)
                try:
                    score = self._minimax(state, depth - 1, alpha, beta)
                finally:
                    state.undo_move(delta)
                if score > value:
                    value = score
                    best_move = move
                alpha = max(alpha, value)
                if alpha >= beta:
                    self.stats.alpha_beta_cutoffs += 1
                    break
        else:
            value = math.inf
            for move in moves:
                delta = state.apply_move(move)
                try:
                    score = self._minimax(state, depth - 1, alpha, beta)
                finally:
                    state.undo_move(delta)
                if score < value:
                    value = score
                    best_move = move
                beta = min(beta, value)
                if alpha >= beta:
                    self.stats.alpha_beta_cutoffs += 1
                    break

        return value

    def _check_timeout(self) -> None:
        if time.perf_counter() >= self.deadline:
            raise SearchTimeout
