# src/run_experiment.py
from phi_evaluator import PhiEvaluator
from easy_agent import EasyAgent
from medium_agent import MediumAgent
from arena import Arena, ArenaAgent

def main():
    # 1. 正常載入與初始化你原本的各種大腦 (與原本網頁端完全對齊)
    phi_evaluator = PhiEvaluator(model="gemma2:2b")
    
    raw_easy = EasyAgent(model_name="qwen2.5:7b")
    raw_medium = MediumAgent(model_name="qwen2.5:7b", phi_evaluator=phi_evaluator)

    # 2. 🔥 採用你的全新包裝器設計：直接把實例丟給 ArenaAgent
    p1_easy_wrapper = ArenaAgent(agent_instance=raw_easy, name="Qwen-Easy")
    p2_medium_wrapper = ArenaAgent(agent_instance=raw_medium, name="Qwen-Medium-Phi")

    # 3. 送進競技場管道進行自動化對打
    pipeline = Arena(p1=p1_easy_wrapper, p2=p2_medium_wrapper)

    # 執行對局（例如自動互刷 10 局，收集勝率與空間幻覺沒收數據）
    # verbose=True 會詳細印出每一步；verbose=False 則安靜顯示進度條
    pipeline.run_benchmark(num_games=10, verbose=False)

if __name__ == "__main__":
    main()