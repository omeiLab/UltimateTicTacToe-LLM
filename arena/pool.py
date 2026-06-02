from LLM.easy_agent import EasyAgent
from LLM.medium_agent import MediumAgent
from LLM.phi_evaluator import PhiEvaluator
from .minimax_adapter import MinimaxAdapter
from arena.arena import ArenaAgent

class AgentPool:
    def __init__(self):
        self._pool = {}
        self.initialize_all_agents()

    def initialize_all_agents(self):
        print("[AgentPool] Initialize...")

        # LLM Easy
        self._pool["easy"] = EasyAgent(model_name="qwen2.5:7b")
        
        # LLM Medium
        gemma_evaluator = PhiEvaluator(model="gemma2:2b")
        self._pool["medium"] = MediumAgent(model_name="qwen2.5:7b", phi_evaluator=gemma_evaluator)

        # Minimax
        self._pool["minimax_X"] = MinimaxAdapter(model_player="X", time_limit=3.0)
        self._pool["minimax_O"] = MinimaxAdapter(model_player="O", time_limit=3.0)
        
        print("[AgentPool] Initialization complete. Agents available:", list(self._pool.keys()))

    def _resolve_key(self, mode_name: str, player_id: int) -> str:
        clean_mode = mode_name.replace("qwen_", "")
        
        if clean_mode == "minimax":
            return "minimax_X" if player_id == 1 else "minimax_O"
        return clean_mode
    
    def get_agent(self, mode_name: str, player_id: int = 2):
        target_key = self._resolve_key(mode_name, player_id)
        if target_key not in self._pool:
            raise ValueError(f"{mode_name} is not a valid agent type.")
        return self._pool[target_key]
    
    def get_arena_agent(self, mode_name: str, player_id: int):
        target_key = self._resolve_key(mode_name, player_id)

        if target_key not in self._pool:
            raise ValueError(f"{mode_name} is not a valid mode. Available modes: {list(self._pool.keys())}")

        raw_brain = self._pool[target_key]
        
        role_name = f"P{player_id}-{mode_name.upper()}"
        return ArenaAgent(agent_instance=raw_brain, name=role_name)

    def prepare_for_new_game(self):
        # Reset agents if they have a reset method (like MinimaxAdapter)
        if "minimax_X" in self._pool:
            self._pool["minimax_X"].reset_agent(starting_player_id=1)
        if "minimax_O" in self._pool:
            self._pool["minimax_O"].reset_agent(starting_player_id=1)

    def get_pool_list(self):
        return list(self._pool.keys())