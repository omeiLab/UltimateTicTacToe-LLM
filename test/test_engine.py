import pytest
from src.engine import UltimateTicTacToeEngine

@pytest.fixture
def engine():
    return UltimateTicTacToeEngine()

def test_initialization(engine):
    assert engine.active_box is None
    assert all(all(all(cell == 0 for cell in row) for row in box) for box in engine.board)

def test_first_move(engine):
    success = engine.make_move(4, 1, 1, 1)
    assert success is True
    assert engine.board[4][1][1] == 1
    assert engine.active_box == 4

def test_invalid_move_out_of_turn(engine):
    engine.make_move(4, 1, 1, 1)
    success = engine.make_move(0, 0, 0, 2)
    assert success is False

def test_active_box_switching(engine):
    engine.make_move(4, 0, 2, 1)
    assert engine.active_box == 2

def test_big_board_win(engine):
    engine.active_box = 0
    engine.make_move(0, 0, 0, 1)
    engine.active_box = 0
    engine.make_move(0, 0, 1, 1)
    engine.active_box = 0
    engine.make_move(0, 0, 2, 1)
    assert engine.big_board[0] == 1 

def test_free_play_after_full_box(engine):
    engine.big_board[4] = 1
    engine.active_box = 4
    
    success = engine.make_move(0, 0, 0, 1)
    invalid = engine.make_move(4, 0, 0, 1) 
    assert success is True
    assert invalid is False