import math
import numpy as np
import torch

WIN_LINES = (
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
)

ACTION_TO_GR = np.empty(81, dtype=np.int8)
ACTION_TO_GC = np.empty(81, dtype=np.int8)
for _a in range(81):
    _m = _a // 9
    _c = _a % 9
    _mr = _m // 3
    _mc = _m % 3
    _lr = _c // 3
    _lc = _c % 3
    ACTION_TO_GR[_a] = _mr * 3 + _lr
    ACTION_TO_GC[_a] = _mc * 3 + _lc


class FastBoard:
    """
    Lightweight clone of UltimateTicTacToeEnv state.

    board[action] stores:
        0  = empty
        1  = O
       -1  = X

    macro[m] stores:
        0  = unfinished micro board
        1  = O won that micro board
       -1  = X won that micro board
        2  = draw / filled micro board
    """

    __slots__ = ("board", "macro", "active", "current")

    def __init__(self, board, macro, active, current):
        self.board = board
        self.macro = macro
        self.active = active
        self.current = current

    @classmethod
    def from_env(cls, env):
        return cls(
            env.board.reshape(81).astype(np.int8, copy=True),
            env.macro_board.astype(np.int8, copy=True),
            int(env.active_micro),
            int(env.current_player),
        )

    def clone(self):
        return FastBoard(
            self.board.copy(),
            self.macro.copy(),
            self.active,
            self.current,
        )

    def legal_actions_list(self):
        board = self.board
        macro = self.macro
        active = self.active

        actions = []

        if active == -1 or macro[active] != 0:
            for m in range(9):
                if macro[m] != 0:
                    continue
                base = m * 9
                for c in range(9):
                    a = base + c
                    if board[a] == 0:
                        actions.append(a)
        else:
            base = active * 9
            for c in range(9):
                a = base + c
                if board[a] == 0:
                    actions.append(a)

        return actions

    def legal_mask_np(self):
        mask = np.zeros(81, dtype=np.int8)
        for a in self.legal_actions_list():
            mask[a] = 1
        return mask

    def check_micro_win(self, m, player):
        board = self.board
        base = m * 9
        for a, b, c in WIN_LINES:
            if (
                board[base + a] == player
                and board[base + b] == player
                and board[base + c] == player
            ):
                return True
        return False

    def check_macro_win(self, player):
        macro = self.macro
        for a, b, c in WIN_LINES:
            if macro[a] == player and macro[b] == player and macro[c] == player:
                return True
        return False

    def micro_full(self, m):
        board = self.board
        base = m * 9
        for c in range(9):
            if board[base + c] == 0:
                return False
        return True

    def macro_full(self):
        macro = self.macro
        for m in range(9):
            if macro[m] == 0:
                return False
        return True

    def play(self, action):
        """
        Apply action.
        Returns:
            1.0 if the player who just moved wins the whole game
            0.0 if game draws
            None if not terminal
        """
        player = self.current
        m = action // 9
        c = action % 9

        self.board[action] = player

        if self.macro[m] == 0:
            if self.check_micro_win(m, player):
                self.macro[m] = player
            elif self.micro_full(m):
                self.macro[m] = 2

        if self.check_macro_win(player):
            self.current = -player
            self.active = -1
            return 1.0

        if self.macro_full():
            self.current = -player
            self.active = -1
            return 0.0

        if self.macro[c] != 0:
            self.active = -1
        else:
            self.active = c

        self.current = -player
        return None

    def terminal_value_for_player_to_move(self):
        """
        Value from the perspective of the player to move.
        In a terminal win state, the previous player won, so current player lost.
        Returns:
            -1.0 if previous player won
             0.0 if draw
             None if non-terminal
        """
        previous_player = -self.current

        if self.check_macro_win(previous_player):
            return -1.0

        if self.macro_full():
            return 0.0

        return None


class MCTS:
    def __init__(self, model, device, c_puct=1.4, num_simulations=200):
        self.model = model
        self.device = device
        self.c_puct = c_puct
        self.num_simulations = num_simulations

    def get_action_prob(self, env, temp=1.0, add_noise=False):
        root_state = FastBoard.from_env(env)

        parents = [-1]
        actions = [-1]
        priors = [0.0]
        visits = [0]
        wins = [0.0]
        children = [{}]

        for _ in range(self.num_simulations):
            state = root_state.clone()
            node = 0

            while children[node]:
                action, next_node = self._select_child_array(
                    node,
                    children,
                    visits,
                    wins,
                    priors,
                )
                state.play(action)
                node = next_node

            terminal_value = state.terminal_value_for_player_to_move()
            if terminal_value is not None:
                self._backpropagate_array(
                    node,
                    terminal_value,
                    parents,
                    visits,
                    wins,
                )
                continue

            legal_actions = state.legal_actions_list()
            if not legal_actions:
                self._backpropagate_array(
                    node,
                    0.0,
                    parents,
                    visits,
                    wins,
                )
                continue

            feature_tensor = self._fast_state_to_tensor(state, legal_actions)

            with torch.inference_mode():
                if self.device.type == "cuda":
                    with torch.amp.autocast("cuda"):
                        policy_logits, value_tensor = self.model(feature_tensor)
                else:
                    policy_logits, value_tensor = self.model(feature_tensor)

            logits = policy_logits.float().detach().cpu().numpy()[0]
            value = float(value_tensor.float().detach().cpu().item())

            legal_logits = logits[legal_actions].astype(np.float64, copy=False)
            legal_logits -= np.max(legal_logits)
            exp_logits = np.exp(legal_logits)
            sum_exp = float(np.sum(exp_logits))

            if sum_exp <= 0.0 or not math.isfinite(sum_exp):
                legal_probs = np.full(
                    len(legal_actions),
                    1.0 / len(legal_actions),
                    dtype=np.float64,
                )
            else:
                legal_probs = exp_logits / sum_exp

            if add_noise and node == 0 and len(legal_actions) > 0:
                alpha = 0.3
                eps = 0.25
                noise = np.random.dirichlet([alpha] * len(legal_actions))
                legal_probs = (1.0 - eps) * legal_probs + eps * noise

            node_children = children[node]
            for act, p in zip(legal_actions, legal_probs):
                child_id = len(parents)
                parents.append(node)
                actions.append(int(act))
                priors.append(float(p))
                visits.append(0)
                wins.append(0.0)
                children.append({})
                node_children[int(act)] = child_id

            self._backpropagate_array(
                node,
                value,
                parents,
                visits,
                wins,
            )

        counts = np.zeros(81, dtype=np.float32)
        for act, child_id in children[0].items():
            counts[act] = visits[child_id]

        if temp <= 1e-2:
            probs = np.zeros(81, dtype=np.float32)
            max_count = float(np.max(counts))

            if max_count <= 0.0:
                legal = env.get_legal_actions().astype(np.float32)
                s = float(np.sum(legal))
                return legal / s if s > 0 else legal

            best_acts = np.flatnonzero(counts == max_count)
            probs[int(np.random.choice(best_acts))] = 1.0
            return probs

        counts64 = counts.astype(np.float64)
        counts64 = counts64 ** (1.0 / temp)
        sum_counts = float(np.sum(counts64))

        if sum_counts <= 0.0 or not math.isfinite(sum_counts):
            legal = env.get_legal_actions().astype(np.float32)
            s = float(np.sum(legal))
            return legal / s if s > 0 else legal

        return (counts64 / sum_counts).astype(np.float32)

    def _select_child_array(self, node, children, visits, wins, priors):
        best_score = -1e100
        best_action = None
        best_child = None

        parent_n = max(1, visits[node])
        sqrt_parent = math.sqrt(parent_n)
        c = self.c_puct

        for action, child_id in children[node].items():
            child_n = visits[child_id]
            q = wins[child_id] / child_n if child_n > 0 else 0.0
            u = c * priors[child_id] * sqrt_parent / (1 + child_n)
            score = q + u

            if score > best_score:
                best_score = score
                best_action = action
                best_child = child_id

        return best_action, best_child

    def _backpropagate_array(self, node, value, parents, visits, wins):
        value = -value

        while node != -1:
            visits[node] += 1
            wins[node] += value
            value = -value
            node = parents[node]

    def _fast_state_to_tensor(self, state, legal_actions):
        board = state.board
        macro = state.macro
        current = state.current

        feature = np.zeros((5, 9, 9), dtype=np.float32)

        occupied = np.flatnonzero(board)
        if occupied.size > 0:
            rows = ACTION_TO_GR[occupied]
            cols = ACTION_TO_GC[occupied]
            vals = board[occupied]

            me = vals == current
            opp = vals == -current

            if np.any(me):
                feature[0, rows[me], cols[me]] = 1.0
            if np.any(opp):
                feature[1, rows[opp], cols[opp]] = 1.0

        if legal_actions:
            legal_arr = np.asarray(legal_actions, dtype=np.int16)
            feature[2, ACTION_TO_GR[legal_arr], ACTION_TO_GC[legal_arr]] = 1.0

        for m in range(9):
            mr = m // 3
            mc = m % 3
            rs = mr * 3
            cs = mc * 3

            if macro[m] == current:
                feature[3, rs:rs + 3, cs:cs + 3] = 1.0
            elif macro[m] == -current:
                feature[4, rs:rs + 3, cs:cs + 3] = 1.0

        return torch.from_numpy(feature).unsqueeze(0).to(self.device, non_blocking=True)

    def _clone_env(self, env):
        new_env = env.__class__()
        new_env.board = env.board.copy()
        new_env.macro_board = env.macro_board.copy()
        new_env.active_micro = env.active_micro
        new_env.current_player = env.current_player
        return new_env

    def _env_obs_to_tensor(self, env, legal_masks):
        state = FastBoard.from_env(env)
        legal_actions = np.flatnonzero(legal_masks).astype(int).tolist()
        return self._fast_state_to_tensor(state, legal_actions)
