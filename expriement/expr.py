from arena.pool import AgentPool
from arena.arena import Arena, ArenaAgent

def run_experiment_matchup(agent_pool: AgentPool, p1_mode: str, p2_mode: str, num_games: int = 10):
    print(f"\n[EXPERIMENT] Preparing Matchup: {p1_mode.upper()} vs {p2_mode.upper()}")
    
    p1_wrapper = agent_pool.get_arena_agent(p1_mode, player_id=1)
    p2_wrapper = agent_pool.get_arena_agent(p2_mode, player_id=2)

    # create an Arena instance for this specific matchup, passing in the agent pool for proper game resets
    pipeline = Arena(p1=p1_wrapper, p2=p2_wrapper, agent_pool=agent_pool)

    # run the benchmark for the specified number of games, with verbose output turned off for cleaner results
    pipeline.run_benchmark(num_games=num_games, verbose=False)

def main():
    agent_pool = AgentPool()
    GAMES_PER_MATCHUP = 10

    run_experiment_matchup(agent_pool, p1_mode="medium", p2_mode="minimax", num_games=GAMES_PER_MATCHUP)
    # run_experiment_matchup(agent_pool, p1_mode="medium", p2_mode="minimax", num_games=GAMES_PER_MATCHUP)
    # run_experiment_matchup(agent_pool, p1_mode="easy", p2_mode="medium", num_games=GAMES_PER_MATCHUP)

if __name__ == "__main__":
    main()