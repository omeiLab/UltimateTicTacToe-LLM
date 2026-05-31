import math
import numpy as np
import torch

class MCTSNode:
    def __init__(self, action=None, p=0.0, parent=None):
        self.action = action
        self.parent = parent
        self.children = {}
        
        self.n = 0
        self.w = 0.0
        self.q = 0.0
        self.p = p

    def is_leaf(self):
        return len(self.children) == 0

    def get_puct(self, c_puct):
        parent_n = self.parent.n if self.parent else 1
        u = c_puct * self.p * math.sqrt(parent_n) / (1 + self.n)
        return self.q + u

    def update(self, value):
        self.n += 1
        self.w += value
        self.q = self.w / self.n


class MCTS:
    def __init__(self, model, device, c_puct=1.4, num_simulations=200):
        self.model = model
        self.device = device
        self.c_puct = c_puct
        self.num_simulations = num_simulations

    def get_action_prob(self, env, temp=1.0, add_noise=False):
        root = MCTSNode()

        for _ in range(self.num_simulations):
            sim_env = self._clone_env(env)
            node = root

            while not node.is_leaf():
                action, node = self._select_child(node)
                sim_env.step(action)

            legal_masks = sim_env.get_legal_actions()

            last_player_won = sim_env._check_3x3_win(
                sim_env.macro_board,
                -sim_env.current_player
            )

            if last_player_won:
                self._backpropagate(node, -1.0)
                continue

            elif np.all(sim_env.macro_board != 0):
                self._backpropagate(node, 0.0)
                continue

            feature_tensor = self._env_obs_to_tensor(sim_env, legal_masks).to(self.device)

            with torch.inference_mode():
                if self.device.type == "cuda":
                    with torch.amp.autocast("cuda"):
                        policy_logits, value_tensor = self.model(feature_tensor)
                else:
                    policy_logits, value_tensor = self.model(feature_tensor)

            policy_logits = policy_logits.float().cpu().numpy()[0]
            v = float(value_tensor.float().cpu().item())

            policy_logits = policy_logits.astype(np.float32)
            policy_logits[legal_masks == 0] = -1e9

            exp_logits = np.exp(policy_logits - np.max(policy_logits))
            probs = exp_logits / np.sum(exp_logits)

            legal_indices = np.where(legal_masks == 1)[0]

            if add_noise and node is root and len(legal_indices) > 0:
                alpha = 0.3
                eps = 0.25
                noise = np.random.dirichlet([alpha] * len(legal_indices))
                probs[legal_indices] = (
                    (1.0 - eps) * probs[legal_indices]
                    + eps * noise
                )

            for act in legal_indices:
                node.children[act] = MCTSNode(
                    action=act,
                    p=float(probs[act]),
                    parent=node
                )

            self._backpropagate(node, v)

        counts = np.array(
            [root.children[act].n if act in root.children else 0 for act in range(81)],
            dtype=np.float32
        )

        if temp <= 1e-2:
            probs = np.zeros(81, dtype=np.float32)

            max_count = np.max(counts)
            best_acts = np.argwhere(counts == max_count).flatten()

            if len(best_acts) == 0 or max_count == 0:
                legal = env.get_legal_actions().astype(np.float32)
                return legal / np.sum(legal)

            probs[np.random.choice(best_acts)] = 1.0
            return probs

        counts = counts.astype(np.float64)
        counts = counts ** (1.0 / temp)

        sum_counts = np.sum(counts)

        if sum_counts <= 0 or np.isnan(sum_counts) or np.isinf(sum_counts):
            legal = env.get_legal_actions().astype(np.float32)
            return legal / np.sum(legal)

        return (counts / sum_counts).astype(np.float32)

    def _select_child(self, node):
        best_score = -float('inf')
        best_action = None
        best_child = None

        for action, child in node.children.items():
            score = child.get_puct(self.c_puct)
            if score > best_score:
                best_score = score
                best_action = action
                best_child = child
        return best_action, best_child

    def _backpropagate(self, node, value):
        value = -value 
    
        while node is not None:
            node.update(value)
            value = -value
            node = node.parent

    def _clone_env(self, env):
        new_env = env.__class__()
        new_env.board = env.board.copy()
        new_env.macro_board = env.macro_board.copy()
        new_env.active_micro = env.active_micro
        new_env.current_player = env.current_player
        return new_env

    def _env_obs_to_tensor(self, env, legal_masks):
        board = env.board
        current_player = env.current_player

        p1_map = np.zeros((9, 9), dtype=np.float32)
        p2_map = np.zeros((9, 9), dtype=np.float32)
        mask_map = np.zeros((9, 9), dtype=np.float32)
        macro_me_map = np.zeros((9, 9), dtype=np.float32)
        macro_opp_map = np.zeros((9, 9), dtype=np.float32)

        for m in range(9):
            macro_row, macro_col = m // 3, m % 3

            r_start = macro_row * 3
            r_end = r_start + 3
            c_start = macro_col * 3
            c_end = c_start + 3

            p1_map[r_start:r_end, c_start:c_end] = (
                board[m] == current_player
            ).astype(np.float32)

            p2_map[r_start:r_end, c_start:c_end] = (
                board[m] == -current_player
            ).astype(np.float32)

            sub_mask = legal_masks[m * 9:(m + 1) * 9].reshape(3, 3)
            mask_map[r_start:r_end, c_start:c_end] = sub_mask.astype(np.float32)

            if env.macro_board[m] == current_player:
                macro_me_map[r_start:r_end, c_start:c_end] = 1.0

            elif env.macro_board[m] == -current_player:
                macro_opp_map[r_start:r_end, c_start:c_end] = 1.0

        feature_tensor = np.stack(
            [
                p1_map,
                p2_map,
                mask_map,
                macro_me_map,
                macro_opp_map
            ],
            axis=0
        )

        return torch.tensor(
            feature_tensor,
            dtype=torch.float32
        ).unsqueeze(0)