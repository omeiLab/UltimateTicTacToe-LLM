import copy

# =========================================================
# BASIC TACTICAL CHECKS
# =========================================================

def is_winning_move(engine, b, r, c, player):
    """
    Check whether placing a move immediately wins the sub-board.
    """

    sim_board = copy.deepcopy(engine.board[b])
    sim_board[r][c] = player

    return engine.check_line_win(sim_board) == player


def is_blocking_move(engine, b, r, c):
    """
    Check whether this move blocks opponent's immediate win.
    """

    sim_board = copy.deepcopy(engine.board[b])
    sim_board[r][c] = 1

    return engine.check_line_win(sim_board) == 1


# =========================================================
# POSITIONAL HEURISTICS
# =========================================================

def positional_score(r, c):

    # center
    if (r, c) == (1, 1):
        return 10

    # corners
    if (r, c) in [(0,0), (0,2), (2,0), (2,2)]:
        return 5

    return 0


# =========================================================
# TACTICAL SCORING
# =========================================================

def tactical_score(engine, b, r, c, player):

    score = 0

    # immediate win
    if is_winning_move(engine, b, r, c, player):
        score += 100

    # block opponent
    if player == 2 and is_blocking_move(engine, b, r, c):
        score += 80

    # positional preference
    score += positional_score(r, c)

    return score


# =========================================================
# OPPONENT SIMULATION
# =========================================================

def simulate_best_reply(engine, opponent_player=1):
    """
    Deterministic greedy opponent simulation.

    Returns:
        (
            best_move,
            best_damage
        )
    """

    legal_moves = engine.get_legal_moves()

    best_move = None
    best_damage = -99999

    for b, r, c in legal_moves:

        damage = tactical_score(
            engine,
            b,
            r,
            c,
            opponent_player
        )

        if damage > best_damage:
            best_damage = damage
            best_move = (b, r, c)

    return best_move, best_damage


# =========================================================
# FALLBACK POLICY
# =========================================================

def fallback_move(legal_moves):

    if not legal_moves:
        return {
            "box": -1,
            "row": -1,
            "col": -1,
            "reason": "[Fallback] No legal moves."
        }

    b, r, c = legal_moves[0]

    return {
        "box": b,
        "row": r,
        "col": c,
        "reason": "[Fallback Move]"
    }