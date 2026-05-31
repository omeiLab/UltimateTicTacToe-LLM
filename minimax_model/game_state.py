from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .bitboard import (
    bit_for_move,
    cell_owner,
    count_by_player,
    count_moves,
    is_cell_empty,
    local_cell,
    opponent,
    set_cell,
    small_board_mask,
    visual_board_to_bitboards,
)
from .exceptions import InvalidInitialStateError
from .lines import ALL_BOARDS_MASK, SMALL_LINES, WIN_MASKS
from .types import GameResult, LastMove, Move, Player, ValidationResult


@dataclass(slots=True)
class MoveDelta:
    move: Move
    player: Player
    previous_x_bits: int
    previous_o_bits: int
    previous_current_turn: Player
    previous_legal_board_mask: int
    previous_game_result: GameResult
    previous_small_board_status: tuple[GameResult, ...]
    previous_last_move: LastMove | None


@dataclass(slots=True)
class GameState:
    x_bits: int
    o_bits: int
    current_turn: Player
    legal_board_mask: int
    game_result: GameResult
    small_board_status: tuple[GameResult, ...]
    last_move: LastMove | None = None

    @classmethod
    def new(cls, starting_player: Player) -> "GameState":
        return cls(
            x_bits=0,
            o_bits=0,
            current_turn=starting_player,
            legal_board_mask=ALL_BOARDS_MASK,
            game_result=None,
            small_board_status=(None,) * 9,
            last_move=None,
        )

    @classmethod
    def from_initial_board(cls, initial_board: dict, starting_player: Player) -> "GameState":
        validate_initial_board_shape(initial_board)
        x_bits, o_bits = visual_board_to_bitboards(initial_board["board"])
        last_move = normalize_last_move(initial_board["last_move"])
        validate_counts(x_bits, o_bits, starting_player, last_move["player"])
        if cell_owner(x_bits, o_bits, last_move["board"], last_move["row"], last_move["col"]) != last_move["player"]:
            raise InvalidInitialStateError("last_move position is not occupied by last_move.player.")
        small_status = derive_small_board_status(x_bits, o_bits)
        game_result = derive_game_result(x_bits, o_bits)
        if game_result is not None:
            raise InvalidInitialStateError("initial_board must not be a terminal board.")
        return cls(
            x_bits=x_bits,
            o_bits=o_bits,
            current_turn=opponent(last_move["player"]),
            legal_board_mask=derive_legal_board_mask(x_bits, o_bits, last_move),
            game_result=game_result,
            small_board_status=small_status,
            last_move=last_move,
        )

    def apply_move(self, move: Move, player: Player | None = None) -> MoveDelta:
        mover = player or self.current_turn
        delta = MoveDelta(
            move={"board": move["board"], "row": move["row"], "col": move["col"]},
            player=mover,
            previous_x_bits=self.x_bits,
            previous_o_bits=self.o_bits,
            previous_current_turn=self.current_turn,
            previous_legal_board_mask=self.legal_board_mask,
            previous_game_result=self.game_result,
            previous_small_board_status=self.small_board_status,
            previous_last_move=None if self.last_move is None else dict(self.last_move),  # type: ignore[arg-type]
        )
        if mover == "X":
            self.x_bits = set_cell(self.x_bits, move["board"], move["row"], move["col"])
        else:
            self.o_bits = set_cell(self.o_bits, move["board"], move["row"], move["col"])
        self.last_move = {
            "board": move["board"],
            "row": move["row"],
            "col": move["col"],
            "player": mover,
        }
        self.small_board_status = derive_small_board_status(self.x_bits, self.o_bits)
        self.game_result = derive_game_result(self.x_bits, self.o_bits)
        self.legal_board_mask = 0 if self.game_result is not None else derive_legal_board_mask(self.x_bits, self.o_bits, move)
        self.current_turn = opponent(mover)
        return delta

    def undo_move(self, delta: MoveDelta) -> None:
        self.x_bits = delta.previous_x_bits
        self.o_bits = delta.previous_o_bits
        self.current_turn = delta.previous_current_turn
        self.legal_board_mask = delta.previous_legal_board_mask
        self.game_result = delta.previous_game_result
        self.small_board_status = delta.previous_small_board_status
        self.last_move = delta.previous_last_move


def normalize_last_move(move: object) -> LastMove:
    if not isinstance(move, dict) or not all(k in move for k in ("board", "row", "col", "player")):
        raise InvalidInitialStateError("last_move must contain board, row, col, and player.")
    if not all(isinstance(move[k], int) for k in ("board", "row", "col")):
        raise InvalidInitialStateError("last_move coordinates must be integers.")
    if not 0 <= move["board"] <= 8 or not 0 <= move["row"] <= 2 or not 0 <= move["col"] <= 2:
        raise InvalidInitialStateError("last_move coordinates are out of range.")
    if move["player"] not in ("X", "O"):
        raise InvalidInitialStateError('last_move.player must be "X" or "O".')
    return {"board": move["board"], "row": move["row"], "col": move["col"], "player": move["player"]}


def validate_initial_board_shape(initial_board: object) -> None:
    if not isinstance(initial_board, dict) or "board" not in initial_board:
        raise InvalidInitialStateError("initial_board must contain board and last_move.")
    if "last_move" not in initial_board or initial_board["last_move"] is None:
        raise InvalidInitialStateError("initial_board.last_move must exist and cannot be None.")


def validate_counts(x_bits: int, o_bits: int, starting_player: Player, last_player: Player) -> None:
    x_count, o_count = count_by_player(x_bits, o_bits)
    if starting_player == "X":
        valid = (x_count == o_count and last_player == "O") or (x_count == o_count + 1 and last_player == "X")
    else:
        valid = (o_count == x_count and last_player == "X") or (o_count == x_count + 1 and last_player == "O")
    if not valid:
        raise InvalidInitialStateError("X/O counts are incompatible with starting_player and last_move.player.")


def _small_status_for_board(x_bits: int, o_bits: int, board: int) -> GameResult:
    x_mask = small_board_mask(x_bits, board)
    o_mask = small_board_mask(o_bits, board)
    for win_mask in WIN_MASKS:
        if x_mask & win_mask == win_mask:
            return "X"
        if o_mask & win_mask == win_mask:
            return "O"
    if (x_mask | o_mask) == ALL_BOARDS_MASK:
        return "D"
    return None


def derive_small_board_status(x_bits: int, o_bits: int) -> tuple[GameResult, ...]:
    return tuple(_small_status_for_board(x_bits, o_bits, board) for board in range(9))


def derive_game_result(x_bits: int, o_bits: int) -> GameResult:
    statuses = derive_small_board_status(x_bits, o_bits)
    x_owned = sum(1 << idx for idx, status in enumerate(statuses) if status == "X")
    o_owned = sum(1 << idx for idx, status in enumerate(statuses) if status == "O")
    for win_mask in WIN_MASKS:
        if x_owned & win_mask == win_mask:
            return "X"
        if o_owned & win_mask == win_mask:
            return "O"
    if all(status is not None for status in statuses):
        return "D"
    return None


def derive_legal_board_mask(x_bits: int, o_bits: int, last_move: Move | LastMove | None) -> int:
    statuses = derive_small_board_status(x_bits, o_bits)
    unfinished = sum(1 << board for board, status in enumerate(statuses) if status is None)
    if last_move is None:
        return unfinished
    target = local_cell(last_move["row"], last_move["col"])
    if unfinished & (1 << target):
        return 1 << target
    return unfinished


def derive_current_turn(starting_player: Player, initial_board: dict | None) -> Player:
    if initial_board is None:
        return starting_player
    return opponent(normalize_last_move(initial_board["last_move"])["player"])


def generate_legal_moves(state: GameState) -> list[Move]:
    if state.game_result is not None:
        return []
    moves: list[Move] = []
    for board in range(9):
        if not (state.legal_board_mask & (1 << board)):
            continue
        if state.small_board_status[board] is not None:
            continue
        for row in range(3):
            for col in range(3):
                if is_cell_empty(state.x_bits, state.o_bits, board, row, col):
                    moves.append({"board": board, "row": row, "col": col})
    return moves


def _validate_move_shape(move: object) -> ValidationResult:
    if not isinstance(move, dict) or not all(k in move for k in ("board", "row", "col")):
        return ValidationResult(False, "INVALID_MOVE_FORMAT", "Move must contain board, row, and col.")
    if not all(isinstance(move[k], int) for k in ("board", "row", "col")):
        return ValidationResult(False, "INVALID_MOVE_FORMAT", "Move coordinates must be integers.")
    if not 0 <= move["board"] <= 8 or not 0 <= move["row"] <= 2 or not 0 <= move["col"] <= 2:
        return ValidationResult(False, "MOVE_OUT_OF_RANGE", "Move coordinates are out of range.")
    return ValidationResult(True)


def validate_move_for_player(state: GameState, move: object, player: Player, wrong_turn_code: str) -> ValidationResult:
    shape = _validate_move_shape(move)
    if not shape.ok:
        return shape
    typed = move  # type: ignore[assignment]
    if state.game_result is not None:
        return ValidationResult(False, "GAME_ALREADY_OVER", "Game is already over.")
    if state.current_turn != player:
        return ValidationResult(False, wrong_turn_code, "It is not this player's turn.")
    board = typed["board"]
    if state.small_board_status[board] is not None:
        return ValidationResult(False, "BOARD_CLOSED", "Target board is already closed.")
    if not (state.legal_board_mask & (1 << board)):
        return ValidationResult(False, "BOARD_NOT_LEGAL", "Target board is not legal in the current state.")
    if not is_cell_empty(state.x_bits, state.o_bits, board, typed["row"], typed["col"]):
        return ValidationResult(False, "CELL_OCCUPIED", "Target cell is already occupied.")
    return ValidationResult(True)


def validate_opponent_move(state: GameState, move: object, opponent_player: Player) -> ValidationResult:
    return validate_move_for_player(state, move, opponent_player, "NOT_OPPONENT_TURN")


def debug_validate_model_move(state: GameState, move: object, model_player: Player) -> ValidationResult:
    result = validate_move_for_player(state, move, model_player, "NOT_MODEL_TURN")
    if not result.ok:
        return result
    if move not in generate_legal_moves(state):
        return ValidationResult(False, "MODEL_MOVE_NOT_GENERATED", "Model move was not generated as legal.")
    return result


def is_move_legal(state: GameState, move: Move) -> bool:
    return validate_move_for_player(state, move, state.current_turn, "WRONG_TURN").ok


def move_wins_small_board(state: GameState, move: Move, player: Player) -> bool:
    if state.small_board_status[move["board"]] is not None:
        return False
    bits = state.x_bits if player == "X" else state.o_bits
    bits |= bit_for_move(move["board"], move["row"], move["col"])
    mask = small_board_mask(bits, move["board"])
    return any(mask & win_mask == win_mask for win_mask in WIN_MASKS)


def player_has_two_line_threat(state: GameState, board: int, cell: int, player: Player) -> bool:
    if state.small_board_status[board] is not None:
        return False
    player_mask = small_board_mask(state.x_bits if player == "X" else state.o_bits, board)
    other_mask = small_board_mask(state.o_bits if player == "X" else state.x_bits, board)
    for line in SMALL_LINES:
        if cell in line:
            line_mask = sum(1 << c for c in line)
            if other_mask & line_mask:
                continue
            if (player_mask & line_mask).bit_count() == 2:
                return True
    return False


def move_wins_game_by_small_board(state: GameState, move: Move, player: Player) -> bool:
    if not move_wins_small_board(state, move, player):
        return False
    statuses = list(state.small_board_status)
    statuses[move["board"]] = player
    owned = sum(1 << idx for idx, status in enumerate(statuses) if status == player)
    return any(owned & win_mask == win_mask for win_mask in WIN_MASKS)


def move_blocks_global_win(state: GameState, move: Move, player: Player) -> bool:
    if not move_wins_small_board(state, move, player):
        return False
    other = opponent(player)
    statuses = list(state.small_board_status)
    statuses[move["board"]] = player
    other_owned_before = sum(1 << idx for idx, status in enumerate(state.small_board_status) if status == other)
    for win_mask in WIN_MASKS:
        if not (win_mask & (1 << move["board"])):
            continue
        if (other_owned_before & win_mask).bit_count() == 2:
            return True
    return False


def total_moves(state: GameState) -> int:
    return count_moves(state.x_bits, state.o_bits)
