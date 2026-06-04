import os
import random
import time
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from collections import deque
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

from uttt_env import UltimateTicTacToeEnv
from RL import UTTTNet
from mcts import MCTS


torch.backends.cudnn.benchmark = True

if torch.cuda.is_available():
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    torch.set_float32_matmul_precision("high")


START_ITER = 171
NUM_ITERATIONS = 200

RESUME_PATH = "checkpoints/uttt_model_iter_170.pth"

NUM_EPISODES = 30
NUM_SELF_PLAY_EPISODES = 30
NUM_MINIMAX_EPISODES = 3
NUM_OLD_CHECKPOINT_EPISODES = 7

NUM_SIMULATIONS = 120
OLD_OPPONENT_SIMULATIONS = 50

BATCH_SIZE = 256
EPOCHS = 2

LEARNING_RATE = 0.00015
BUFFER_SIZE = 100000

MINIMAX_DEPTH = 3

OLD_CHECKPOINT_PATHS = [
    "checkpoints/uttt_model_iter_30.pth",
    "checkpoints/uttt_model_iter_40.pth",
    "checkpoints/uttt_model_iter_50.pth",
    "checkpoints/uttt_model_iter_60.pth",
    "checkpoints/uttt_model_iter_70.pth",
    "checkpoints/uttt_model_iter_80.pth",
    "checkpoints/uttt_model_iter_90.pth",
    "checkpoints/uttt_model_iter_100.pth",
    "checkpoints/uttt_model_iter_110.pth",
    "checkpoints/uttt_model_iter_120.pth",
    "checkpoints/uttt_model_iter_130.pth",
    "checkpoints/uttt_model_iter_140.pth",
    "checkpoints/uttt_model_iter_150.pth",
    "checkpoints/uttt_model_iter_160.pth",
    "checkpoints/uttt_model_iter_170.pth",
]

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class AlphaZeroDataset(Dataset):
    def __init__(self, buffer):
        self.buffer = buffer

    def __len__(self):
        return len(self.buffer)

    def __getitem__(self, idx):
        state, pi, z = self.buffer[idx]

        return (
            torch.tensor(state, dtype=torch.float32),
            torch.tensor(pi, dtype=torch.float32),
            torch.tensor([z], dtype=torch.float32)
        )


def get_feature_map(env, legal_masks):
    board = env.board
    current_player = env.current_player

    p1_map = np.zeros((9, 9), dtype=np.float32)
    p2_map = np.zeros((9, 9), dtype=np.float32)
    mask_map = np.zeros((9, 9), dtype=np.float32)
    macro_me_map = np.zeros((9, 9), dtype=np.float32)
    macro_opp_map = np.zeros((9, 9), dtype=np.float32)

    for m in range(9):
        macro_row = m // 3
        macro_col = m % 3

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

        sub_mask = legal_masks[
            m * 9:(m + 1) * 9
        ].reshape(3, 3)

        mask_map[r_start:r_end, c_start:c_end] = (
            sub_mask.astype(np.float32)
        )

        if env.macro_board[m] == current_player:
            macro_me_map[r_start:r_end, c_start:c_end] = 1.0

        elif env.macro_board[m] == -current_player:
            macro_opp_map[r_start:r_end, c_start:c_end] = 1.0

    return np.stack(
        [
            p1_map,
            p2_map,
            mask_map,
            macro_me_map,
            macro_opp_map
        ],
        axis=0
    )


def action_pi_to_grid(pi):
    grid = np.zeros((9, 9), dtype=np.float32)

    for action in range(81):
        micro_idx = action // 9
        cell_idx = action % 9

        local_row = cell_idx // 3
        local_col = cell_idx % 3

        macro_row = micro_idx // 3
        macro_col = micro_idx % 3

        global_row = macro_row * 3 + local_row
        global_col = macro_col * 3 + local_col

        grid[global_row, global_col] = pi[action]

    return grid


def grid_to_action_pi(grid):
    pi = np.zeros(81, dtype=np.float32)

    for action in range(81):
        micro_idx = action // 9
        cell_idx = action % 9

        local_row = cell_idx // 3
        local_col = cell_idx % 3

        macro_row = micro_idx // 3
        macro_col = micro_idx % 3

        global_row = macro_row * 3 + local_row
        global_col = macro_col * 3 + local_col

        pi[action] = grid[global_row, global_col]

    return pi


def get_symmetries(state_tensor, pi):
    symm_data = []

    pi_board = action_pi_to_grid(pi)

    for k in range(4):
        new_state = np.rot90(
            state_tensor,
            k=k,
            axes=(1, 2)
        )

        new_pi_board = np.rot90(
            pi_board,
            k=k
        )

        new_pi = grid_to_action_pi(new_pi_board)

        pi_sum = np.sum(new_pi)
        if pi_sum > 0:
            new_pi = new_pi / pi_sum

        symm_data.append(
            (
                new_state.copy(),
                new_pi.copy()
            )
        )

        flip_state = np.flip(
            new_state,
            axis=2
        )

        flip_pi_board = np.flip(
            new_pi_board,
            axis=1
        )

        flip_pi = grid_to_action_pi(flip_pi_board)

        pi_sum = np.sum(flip_pi)
        if pi_sum > 0:
            flip_pi = flip_pi / pi_sum

        symm_data.append(
            (
                flip_state.copy(),
                flip_pi.copy()
            )
        )

    return symm_data


class MinimaxAgent:
    def __init__(self, depth=3, name="Minimax"):
        self.depth = depth
        self.name = name

    def get_action(self, env):
        root_player = env.current_player

        legal_masks = env.get_legal_actions()
        legal_actions = np.where(legal_masks == 1)[0]

        best_score = -float("inf")
        best_actions = []

        alpha = -float("inf")
        beta = float("inf")

        for action in legal_actions:
            sim_env = self._clone_env(env)

            _, reward, terminated, info = sim_env.step(int(action))

            if terminated:
                score = self._terminal_value(
                    reward,
                    info,
                    root_player
                )
            else:
                score = self._minimax(
                    sim_env,
                    depth=self.depth - 1,
                    alpha=alpha,
                    beta=beta,
                    maximizing=False,
                    root_player=root_player
                )

            if score > best_score:
                best_score = score
                best_actions = [int(action)]

            elif score == best_score:
                best_actions.append(int(action))

            alpha = max(alpha, best_score)

        return int(np.random.choice(best_actions))

    def _minimax(
        self,
        env,
        depth,
        alpha,
        beta,
        maximizing,
        root_player
    ):
        legal_masks = env.get_legal_actions()
        legal_actions = np.where(legal_masks == 1)[0]

        if depth == 0 or len(legal_actions) == 0:
            return self._evaluate(env, root_player)

        if maximizing:
            value = -float("inf")

            for action in legal_actions:
                sim_env = self._clone_env(env)

                _, reward, terminated, info = sim_env.step(int(action))

                if terminated:
                    score = self._terminal_value(
                        reward,
                        info,
                        root_player
                    )
                else:
                    score = self._minimax(
                        sim_env,
                        depth - 1,
                        alpha,
                        beta,
                        False,
                        root_player
                    )

                value = max(value, score)
                alpha = max(alpha, value)

                if alpha >= beta:
                    break

            return value

        else:
            value = float("inf")

            for action in legal_actions:
                sim_env = self._clone_env(env)

                _, reward, terminated, info = sim_env.step(int(action))

                if terminated:
                    score = self._terminal_value(
                        reward,
                        info,
                        root_player
                    )
                else:
                    score = self._minimax(
                        sim_env,
                        depth - 1,
                        alpha,
                        beta,
                        True,
                        root_player
                    )

                value = min(value, score)
                beta = min(beta, value)

                if alpha >= beta:
                    break

            return value

    def _terminal_value(self, reward, info, root_player):
        if reward == 0:
            return 0.0

        winner = info["last_player"]

        if winner == root_player:
            return 100000.0

        return -100000.0

    def _evaluate(self, env, root_player):
        opponent = -root_player
        score = 0.0

        score += self._evaluate_macro_board(
            env.macro_board,
            root_player
        ) * 100.0

        score -= self._evaluate_macro_board(
            env.macro_board,
            opponent
        ) * 100.0

        for m in range(9):
            if env.macro_board[m] == root_player:
                score += 500.0

            elif env.macro_board[m] == opponent:
                score -= 500.0

            elif env.macro_board[m] == 0:
                score += self._evaluate_micro_board(
                    env.board[m],
                    root_player
                )

                score -= self._evaluate_micro_board(
                    env.board[m],
                    opponent
                )

        if env.macro_board[4] == root_player:
            score += 120.0

        elif env.macro_board[4] == opponent:
            score -= 120.0

        legal_count = np.sum(env.get_legal_actions())
        score += 0.5 * legal_count

        return score

    def _evaluate_macro_board(self, macro_board, player):
        b = macro_board.reshape(3, 3)
        score = 0.0

        lines = self._get_lines(b)

        for line in lines:
            score += self._score_line(
                line,
                player,
                macro=True
            )

        return score

    def _evaluate_micro_board(self, board_3x3, player):
        score = 0.0

        lines = self._get_lines(board_3x3)

        for line in lines:
            score += self._score_line(
                line,
                player,
                macro=False
            )

        if board_3x3[1, 1] == player:
            score += 3.0

        corners = [
            board_3x3[0, 0],
            board_3x3[0, 2],
            board_3x3[2, 0],
            board_3x3[2, 2],
        ]

        score += corners.count(player) * 1.5

        return score

    def _score_line(self, line, player, macro=False):
        line = list(line)

        if 2 in line:
            return 0.0

        player_count = line.count(player)
        empty_count = line.count(0)

        if player_count == 3:
            return 1000.0 if macro else 100.0

        if player_count == 2 and empty_count == 1:
            return 80.0 if macro else 12.0

        if player_count == 1 and empty_count == 2:
            return 10.0 if macro else 2.0

        return 0.0

    def _get_lines(self, b):
        return [
            b[0, :],
            b[1, :],
            b[2, :],
            b[:, 0],
            b[:, 1],
            b[:, 2],
            np.array([b[0, 0], b[1, 1], b[2, 2]]),
            np.array([b[0, 2], b[1, 1], b[2, 0]]),
        ]

    def _clone_env(self, env):
        new_env = env.__class__()
        new_env.board = env.board.copy()
        new_env.macro_board = env.macro_board.copy()
        new_env.active_micro = env.active_micro
        new_env.current_player = env.current_player
        return new_env


class OldCheckpointPoolAgent:
    def __init__(
        self,
        checkpoint_paths,
        device,
        num_simulations=50,
        c_puct=1.4,
        num_res_blocks=3,
        num_channels=64
    ):
        self.device = device
        self.num_simulations = num_simulations
        self.c_puct = c_puct
        self.models = []
        self.names = []

        for path in checkpoint_paths:
            if not os.path.exists(path):
                print(f"Old checkpoint 不存在，跳過: {path}")
                continue

            model = UTTTNet(
                num_res_blocks=num_res_blocks,
                num_channels=num_channels
            ).to(device)

            state_dict = torch.load(
                path,
                map_location=device,
                weights_only=True
            )

            model.load_state_dict(state_dict)
            model.eval()

            self.models.append(model)
            self.names.append(path)

            print(f"載入 old checkpoint opponent: {path}")

    def has_models(self):
        return len(self.models) > 0

    def get_action(self, env):
        if not self.has_models():
            raise RuntimeError("OldCheckpointPoolAgent 沒有任何可用模型。")

        idx = random.randrange(len(self.models))
        model = self.models[idx]

        mcts_agent = MCTS(
            model,
            self.device,
            c_puct=self.c_puct,
            num_simulations=self.num_simulations
        )

        with torch.inference_mode():
            pi = mcts_agent.get_action_prob(
                env,
                temp=0,
                add_noise=False
            )

        return int(np.argmax(pi))


def execute_self_play_episode(model, agent):
    env = UltimateTicTacToeEnv()
    env.reset()

    episode_data = []
    terminated = False

    while not terminated:
        legal_masks = env.get_legal_actions()

        state_tensor = get_feature_map(
            env,
            legal_masks
        )

        if len(episode_data) < 20:
            temp = 1.0
        else:
            temp = 0.5

        pi = agent.get_action_prob(
            env,
            temp=temp,
            add_noise=True
        )

        episode_data.append(
            [
                state_tensor,
                pi,
                env.current_player
            ]
        )

        action = np.random.choice(
            81,
            p=pi
        )

        obs, reward, terminated, info = env.step(action)

    refined_data = []

    if reward == 1:
        final_winner = info["last_player"]
    else:
        final_winner = 0

    for state_tensor, pi, player in episode_data:
        if final_winner == 0:
            z = 0.0
        elif player == final_winner:
            z = 1.0
        else:
            z = -1.0

        for aug_state, aug_pi in get_symmetries(
            state_tensor,
            pi
        ):
            refined_data.append(
                (
                    aug_state,
                    aug_pi,
                    z
                )
            )

    return refined_data


def execute_minimax_episode(model, rl_agent, minimax_agent):
    env = UltimateTicTacToeEnv()
    env.reset()

    rl_player = random.choice([1, -1])

    episode_data = []
    terminated = False
    rl_move_count = 0

    while not terminated:
        current_player = env.current_player

        if current_player == rl_player:
            legal_masks = env.get_legal_actions()

            state_tensor = get_feature_map(
                env,
                legal_masks
            )

            if rl_move_count < 20:
                temp = 1.0
            else:
                temp = 0.5

            pi = rl_agent.get_action_prob(
                env,
                temp=temp,
                add_noise=True
            )

            episode_data.append(
                [
                    state_tensor,
                    pi,
                    current_player
                ]
            )

            action = np.random.choice(
                81,
                p=pi
            )

            rl_move_count += 1

        else:
            action = minimax_agent.get_action(env)

        obs, reward, terminated, info = env.step(int(action))

    refined_data = []

    if reward == 1:
        final_winner = info["last_player"]
    else:
        final_winner = 0

    for state_tensor, pi, player in episode_data:
        if final_winner == 0:
            z = 0.0
        elif player == final_winner:
            z = 1.0
        else:
            z = -1.0

        for aug_state, aug_pi in get_symmetries(
            state_tensor,
            pi
        ):
            refined_data.append(
                (
                    aug_state,
                    aug_pi,
                    z
                )
            )

    return refined_data




def execute_old_checkpoint_episode(model, rl_agent, old_checkpoint_agent):
    env = UltimateTicTacToeEnv()
    env.reset()

    rl_player = random.choice([1, -1])

    episode_data = []
    terminated = False
    rl_move_count = 0

    while not terminated:
        current_player = env.current_player

        if current_player == rl_player:
            legal_masks = env.get_legal_actions()

            state_tensor = get_feature_map(
                env,
                legal_masks
            )

            if rl_move_count < 20:
                temp = 1.0
            else:
                temp = 0.5

            pi = rl_agent.get_action_prob(
                env,
                temp=temp,
                add_noise=True
            )

            episode_data.append(
                [
                    state_tensor,
                    pi,
                    current_player
                ]
            )

            action = np.random.choice(
                81,
                p=pi
            )

            rl_move_count += 1

        else:
            action = old_checkpoint_agent.get_action(env)

        obs, reward, terminated, info = env.step(int(action))

    refined_data = []

    if reward == 1:
        final_winner = info["last_player"]
    else:
        final_winner = 0

    for state_tensor, pi, player in episode_data:
        if final_winner == 0:
            z = 0.0
        elif player == final_winner:
            z = 1.0
        else:
            z = -1.0

        for aug_state, aug_pi in get_symmetries(
            state_tensor,
            pi
        ):
            refined_data.append(
                (
                    aug_state,
                    aug_pi,
                    z
                )
            )

    return refined_data


def main():
    print(f"訓練硬體: {DEVICE}")

    if torch.cuda.is_available():
        print(f"顯卡型號: {torch.cuda.get_device_name(0)}")

    print("\n========== 訓練設定 ==========")
    print(f"START_ITER: {START_ITER}")
    print(f"NUM_ITERATIONS: {NUM_ITERATIONS}")
    print(f"RESUME_PATH: {RESUME_PATH}")
    print(f"NUM_EPISODES per iter: {NUM_EPISODES}")
    print(f"Self-play episodes: {NUM_SELF_PLAY_EPISODES}")
    print(f"Minimax episodes: {NUM_MINIMAX_EPISODES}")
    print(f"Old checkpoint episodes: {NUM_OLD_CHECKPOINT_EPISODES}")
    print(f"NUM_SIMULATIONS: {NUM_SIMULATIONS}")
    print(f"OLD_OPPONENT_SIMULATIONS: {OLD_OPPONENT_SIMULATIONS}")
    print(f"MINIMAX_DEPTH: {MINIMAX_DEPTH}")
    print(f"BATCH_SIZE: {BATCH_SIZE}")
    print(f"EPOCHS: {EPOCHS}")
    print(f"LEARNING_RATE: {LEARNING_RATE}")
    print(f"BUFFER_SIZE: {BUFFER_SIZE}")

    if "OLD_CHECKPOINT_PATHS" in globals():
        print("OLD_CHECKPOINT_PATHS:")
        for path in OLD_CHECKPOINT_PATHS:
            print(f"  - {path}")

    print("================================\n")

    model = UTTTNet(
        num_res_blocks=3,
        num_channels=64
    ).to(DEVICE)

    if os.path.exists(RESUME_PATH):
        state_dict = torch.load(
            RESUME_PATH,
            map_location=DEVICE,
            weights_only=True
        )

        model.load_state_dict(state_dict)

        print(
            f"已從 {RESUME_PATH} 載入模型，"
            f"準備從 iter {START_ITER} 接續訓練。"
        )

    else:
        raise FileNotFoundError(
            f"找不到 RESUME_PATH: {RESUME_PATH}，"
            f"請確認 checkpoint 是否存在。"
        )

    optimizer = optim.Adam(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=1e-4
    )

    mse_loss = nn.MSELoss()

    def alpha_zero_loss(p_logits, target_pi, v_pred, target_z):
        log_p = torch.log_softmax(
            p_logits,
            dim=1
        )

        policy_loss = -torch.mean(
            torch.sum(
                target_pi * log_p,
                dim=1
            )
        )

        value_loss = mse_loss(
            v_pred,
            target_z
        )

        return policy_loss + value_loss

    replay_buffer = deque(
        maxlen=BUFFER_SIZE
    )

    os.makedirs(
        "checkpoints",
        exist_ok=True
    )

    scaler = torch.amp.GradScaler("cuda") if DEVICE.type == "cuda" else None

    minimax_agent = MinimaxAgent(
        depth=MINIMAX_DEPTH,
        name=f"Minimax_depth{MINIMAX_DEPTH}"
    )

    old_checkpoint_agent = None
    old_pool_available = False

    if "OLD_CHECKPOINT_PATHS" in globals() and len(OLD_CHECKPOINT_PATHS) > 0:
        old_checkpoint_agent = OldCheckpointPoolAgent(
            checkpoint_paths=OLD_CHECKPOINT_PATHS,
            device=DEVICE,
            num_simulations=OLD_OPPONENT_SIMULATIONS,
            c_puct=1.4,
            num_res_blocks=3,
            num_channels=64
        )

        old_pool_available = old_checkpoint_agent.has_models()

    if old_pool_available:
        print("Old checkpoint pool 可用。")
    else:
        print("Old checkpoint pool 沒有可用模型。")
        print("Old checkpoint 對戰場次會自動改成 self-play。")

    print(
        f"\n從 iter {START_ITER} 開始訓練："
        f"{NUM_SELF_PLAY_EPISODES} self-play + "
        f"{NUM_MINIMAX_EPISODES} minimax + "
        f"{NUM_OLD_CHECKPOINT_EPISODES} old-checkpoint\n"
    )

    for i in range(START_ITER, NUM_ITERATIONS + 1):
        print(f"\n--- 代數 (Iteration) {i} / {NUM_ITERATIONS} ---")

        model.eval()

        rl_agent = MCTS(
            model,
            DEVICE,
            c_puct=1.4,
            num_simulations=NUM_SIMULATIONS
        )

        new_data_count = 0

        actual_self_play_episodes = NUM_SELF_PLAY_EPISODES
        actual_old_checkpoint_episodes = NUM_OLD_CHECKPOINT_EPISODES

        if not old_pool_available:
            actual_self_play_episodes += NUM_OLD_CHECKPOINT_EPISODES
            actual_old_checkpoint_episodes = 0

        pbar_self = tqdm(
            range(actual_self_play_episodes),
            desc=f"Iter {i} Self-play"
        )

        for _ in pbar_self:
            episode_data = execute_self_play_episode(
                model,
                rl_agent
            )

            replay_buffer.extend(
                episode_data
            )

            new_data_count += len(
                episode_data
            )

            pbar_self.set_postfix(
                {
                    "Buffer": len(replay_buffer),
                    "NewData": new_data_count
                }
            )

        pbar_minimax = tqdm(
            range(NUM_MINIMAX_EPISODES),
            desc=f"Iter {i} RL vs Minimax"
        )

        for _ in pbar_minimax:
            episode_data = execute_minimax_episode(
                model,
                rl_agent,
                minimax_agent
            )

            replay_buffer.extend(
                episode_data
            )

            new_data_count += len(
                episode_data
            )

            pbar_minimax.set_postfix(
                {
                    "Buffer": len(replay_buffer),
                    "NewData": new_data_count
                }
            )

        if actual_old_checkpoint_episodes > 0:
            pbar_old = tqdm(
                range(actual_old_checkpoint_episodes),
                desc=f"Iter {i} RL vs OldPool"
            )

            for _ in pbar_old:
                episode_data = execute_old_checkpoint_episode(
                    model,
                    rl_agent,
                    old_checkpoint_agent
                )

                replay_buffer.extend(
                    episode_data
                )

                new_data_count += len(
                    episode_data
                )

                pbar_old.set_postfix(
                    {
                        "Buffer": len(replay_buffer),
                        "NewData": new_data_count
                    }
                )

        model.train()

        dataset = AlphaZeroDataset(
            replay_buffer
        )

        num_workers = 0 if os.name == "nt" else 2

        dataloader = DataLoader(
            dataset,
            batch_size=BATCH_SIZE,
            shuffle=True,
            drop_last=True,
            num_workers=num_workers,
            pin_memory=True if DEVICE.type == "cuda" else False
        )

        print(
            f"開始訓練網路，"
            f"資料集大小: {len(dataset)}，"
            f"本輪新增資料: {new_data_count}"
        )

        total_loss = 0.0

        for epoch in range(EPOCHS):
            epoch_loss = 0.0

            for batch_states, batch_pis, batch_zs in dataloader:
                batch_states = batch_states.to(
                    DEVICE,
                    non_blocking=True
                )

                batch_pis = batch_pis.to(
                    DEVICE,
                    non_blocking=True
                )

                batch_zs = batch_zs.to(
                    DEVICE,
                    non_blocking=True
                )

                optimizer.zero_grad()

                if scaler:
                    with torch.amp.autocast("cuda"):
                        p_logits, v_pred = model(
                            batch_states
                        )

                        loss = alpha_zero_loss(
                            p_logits,
                            batch_pis,
                            v_pred,
                            batch_zs
                        )

                    scaler.scale(loss).backward()
                    scaler.step(optimizer)
                    scaler.update()

                else:
                    p_logits, v_pred = model(
                        batch_states
                    )

                    loss = alpha_zero_loss(
                        p_logits,
                        batch_pis,
                        v_pred,
                        batch_zs
                    )

                    loss.backward()
                    optimizer.step()

                epoch_loss += loss.item()

            avg_epoch_loss = epoch_loss / max(
                1,
                len(dataloader)
            )

            total_loss += epoch_loss

            print(
                f"   Epoch {epoch + 1}/{EPOCHS} | "
                f"Loss: {avg_epoch_loss:.4f}"
            )

        checkpoint_path = f"checkpoints/uttt_model_iter_{i}.pth"

        torch.save(
            model.state_dict(),
            checkpoint_path
        )

        print(f"權重已儲存至: {checkpoint_path}")

    torch.save(
        model.state_dict(),
        "best_uttt_model.pth"
    )

    print(
        f"\niter{START_ITER}~iter{NUM_ITERATIONS} 訓練完成！"
        f"最終權重已儲存為 best_uttt_model.pth"
    )


if __name__ == "__main__":
    main()