import time
import os
import torch
import numpy as np

from uttt_env import UltimateTicTacToeEnv
from RL import UTTTNet
from mcts import MCTS


DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class RLAgent:
    def __init__(
        self,
        model_path,
        num_simulations=200,
        c_puct=1.4,
        num_res_blocks=3,
        num_channels=64,
        name="RLAgent"
    ):
        self.name = name
        self.model_path = model_path

        self.model = UTTTNet(
            num_res_blocks=num_res_blocks,
            num_channels=num_channels
        ).to(DEVICE)

        if os.path.exists(model_path):
            try:
                state_dict = torch.load(
                model_path,
                map_location=DEVICE,
                weights_only=True
            )

                self.model.load_state_dict(state_dict)

                print(f"成功載入 RL 權重: {model_path}")

            except RuntimeError as e:
                print("\n權重載入失敗！")
                print(f"檔案路徑: {model_path}")
                print("\n常見原因：")
                print("1. 你把 UTTTNet input channel 從 3 改成 5")
                print("2. 但是這個 checkpoint 是舊版 3-channel 模型訓練出來的")
                print("3. 因此 shape 對不上，不能直接 load")
                print("\n解法：")
                print("請用新版 RL.py / train.py 重新訓練模型。")
                print("\nPyTorch 錯誤訊息：")
                print(e)
                raise e

        else:
            print(f"找不到權重檔案 {model_path}，將使用隨機初始化模型進行測試。")

        self.model.eval()

        self.mcts = MCTS(
            self.model,
            DEVICE,
            c_puct=c_puct,
            num_simulations=num_simulations
        )

    def get_action(self, env):
        start_time = time.time()

        self.model.eval()

        with torch.no_grad():
            action_probs = self.mcts.get_action_prob(
                env,
                temp=0,
                add_noise=False
            )

        action = int(np.argmax(action_probs))

        latency = time.time() - start_time

        return action, latency


def play_match(agent_o, agent_x, render_game=False):
    env = UltimateTicTacToeEnv()
    env.reset()

    terminated = False

    o_latencies = []
    x_latencies = []
    total_steps = 0

    if render_game:
        print("\n=== 初始棋盤 ===")
        env.render()

    while not terminated:
        total_steps += 1
        current_player = env.current_player

        if current_player == 1:
            action, latency = agent_o.get_action(env)
            o_latencies.append(latency)

        else:
            action, latency = agent_x.get_action(env)
            x_latencies.append(latency)

        try:
            _, reward, terminated, info = env.step(action)

        except ValueError as e:
            print("\nAgent 產生非法走法！")
            print(f"目前玩家: {current_player}")
            print(f"非法 action: {action}")
            print("目前棋盤：")
            env.render()
            raise e

        if render_game:
            print(
                f"\n步數 {total_steps} | "
                f"玩家 {'O' if current_player == 1 else 'X'} 下在: {action}"
            )
            env.render()
            time.sleep(0.1)

    if reward == 1:
        winner = 1 if info["last_player"] == 1 else -1

    else:
        winner = 0

    return winner, total_steps, o_latencies, x_latencies


def run_arena_series(
    agent_1,
    agent_2,
    num_games=10,
    name_1="Agent_1",
    name_2="Agent_2",
    render_single_game=True
):
    print("\n========================================================")
    print(f" ⚔️  競技場對決啟動: {name_1} VS {name_2} | 共 {num_games} 場")
    print("========================================================")

    agent_1_wins = 0
    agent_2_wins = 0
    draws = 0

    winning_steps_list = []

    agent_1_all_latencies = []
    agent_2_all_latencies = []

    agent_1_first_wins = 0
    agent_1_second_wins = 0
    agent_2_first_wins = 0
    agent_2_second_wins = 0

    for g in range(1, num_games + 1):
        should_render = render_single_game and num_games == 1

        if g % 2 != 0:
            winner, steps, o_lats, x_lats = play_match(
                agent_1,
                agent_2,
                render_game=should_render
            )

            agent_1_all_latencies.extend(o_lats)
            agent_2_all_latencies.extend(x_lats)

            if winner == 1:
                game_result = f"{name_1} 先攻勝"
                agent_1_wins += 1
                agent_1_first_wins += 1
                winning_steps_list.append(steps)

            elif winner == -1:
                game_result = f"{name_2} 後攻勝"
                agent_2_wins += 1
                agent_2_second_wins += 1
                winning_steps_list.append(steps)

            else:
                game_result = "平手"
                draws += 1

        else:
            winner, steps, o_lats, x_lats = play_match(
                agent_2,
                agent_1,
                render_game=should_render
            )

            agent_2_all_latencies.extend(o_lats)
            agent_1_all_latencies.extend(x_lats)

            if winner == 1:
                game_result = f"{name_2} 先攻勝"
                agent_2_wins += 1
                agent_2_first_wins += 1
                winning_steps_list.append(steps)

            elif winner == -1:
                game_result = f"{name_1} 後攻勝"
                agent_1_wins += 1
                agent_1_second_wins += 1
                winning_steps_list.append(steps)

            else:
                game_result = "平手"
                draws += 1

        if num_games > 1:
            print(
                f"場次 {g:02d}/{num_games:02d} | "
                f"總步數: {steps:02d} | "
                f"結果: {game_result}"
            )

    total_matches = num_games

    win_rate_1 = agent_1_wins / total_matches * 100.0
    win_rate_2 = agent_2_wins / total_matches * 100.0
    draw_rate = draws / total_matches * 100.0

    avg_steps = np.mean(winning_steps_list) if winning_steps_list else 0.0

    avg_lat_1 = np.mean(agent_1_all_latencies) if agent_1_all_latencies else 0.0
    avg_lat_2 = np.mean(agent_2_all_latencies) if agent_2_all_latencies else 0.0

    med_lat_1 = np.median(agent_1_all_latencies) if agent_1_all_latencies else 0.0
    med_lat_2 = np.median(agent_2_all_latencies) if agent_2_all_latencies else 0.0

    print("\n====== Arena Metrics Report ======")
    print(f"對戰組合: {name_1} vs {name_2}")
    print("--------------------------------------")

    print("1) Win Rate")
    print(f"   - {name_1} 勝率: {win_rate_1:.2f}% ({agent_1_wins} 場)")
    print(f"     · 先攻勝: {agent_1_first_wins} 場")
    print(f"     · 後攻勝: {agent_1_second_wins} 場")
    print(f"   - {name_2} 勝率: {win_rate_2:.2f}% ({agent_2_wins} 場)")
    print(f"     · 先攻勝: {agent_2_first_wins} 場")
    print(f"     · 後攻勝: {agent_2_second_wins} 場")
    print(f"   - 平手率: {draw_rate:.2f}% ({draws} 場)")

    print("\n2) Illegality Rate")
    print(f"   - {name_1}: 0.00%")
    print(f"   - {name_2}: 0.00%")

    print("\n3) Decision Latency")
    print(f"   - {name_1} 平均思考時間: {avg_lat_1:.4f} 秒 / 步")
    print(f"   - {name_1} 中位數思考時間: {med_lat_1:.4f} 秒 / 步")
    print(f"   - {name_2} 平均思考時間: {avg_lat_2:.4f} 秒 / 步")
    print(f"   - {name_2} 中位數思考時間: {med_lat_2:.4f} 秒 / 步")

    print("\n4) Winning Steps")
    print(f"   - 完賽場次平均總落子數: {avg_steps:.1f} 步")

    print("======================================\n")

    return {
        "name_1": name_1,
        "name_2": name_2,
        "agent_1_wins": agent_1_wins,
        "agent_2_wins": agent_2_wins,
        "draws": draws,
        "win_rate_1": win_rate_1,
        "win_rate_2": win_rate_2,
        "draw_rate": draw_rate,
        "avg_steps": avg_steps,
        "avg_latency_1": avg_lat_1,
        "avg_latency_2": avg_lat_2,
        "median_latency_1": med_lat_1,
        "median_latency_2": med_lat_2
    }


if __name__ == "__main__":
    print(f"測試硬體: {DEVICE}")

    if torch.cuda.is_available():
        print(f"顯卡型號: {torch.cuda.get_device_name(0)}")

    NUM_GAMES_RANDOM = 20
    NUM_GAMES_ITER_COMPARE = 20

    MCTS_SIMS_RANDOM_TEST = 10
    MCTS_SIMS_ITER_COMPARE = 10

    ITER_1_PATH = "checkpoints/uttt_model_iter_106.pth"
    ITER_2_PATH = "checkpoints/uttt_model_iter_200.pth"
    BEST_PATH = "best_uttt_model.pth"

    rl_agent = RLAgent(
        model_path=ITER_1_PATH,
        num_simulations=MCTS_SIMS_RANDOM_TEST,
        name="RL_iter1"
    )

    rl_agent2 = RLAgent(
        model_path=ITER_2_PATH,
        num_simulations=MCTS_SIMS_RANDOM_TEST,
        name="RL_iter3"
    )

    run_arena_series(
        agent_1=rl_agent,
        agent_2=rl_agent2,
        num_games=100,
        name_1="RL_iter1",
        name_2="RL_iter3"
    )
