from __future__ import annotations

from typing import Iterable, Dict, Any, Optional

from trading_bot.core.runner import BotRunner
from trading_bot.state.persistence import PersistentStateStore


class StreamPipeline:
    """
    Simple streaming pipeline that feeds bars to BotRunner, optionally persisting risk/belief state.
    """

    def __init__(
        self,
        contracts_path: str = "src/trading_bot/contracts",
        db_path: str = "data/events.sqlite",
        state_path: Optional[str] = None,
    ):
        self.state_store = PersistentStateStore(state_path) if state_path else None
        self.runner = BotRunner(contracts_path=contracts_path, db_path=db_path)
        # Inject persisted belief state if available
        if self.state_store:
            self.state_store.load()
            belief_state = self.state_store.get_belief_state()
            if belief_state:
                self.runner._belief_state["beliefs_state"] = belief_state

    def process(self, bars: Iterable[Dict[str, Any]], stream_id: str = "MES_RTH"):
        last_decision = None
        for bar in bars:
            last_decision = self.runner.run_once(bar, stream_id=stream_id)
            # Persist belief state after each bar
            if self.state_store:
                self.state_store.set_belief_state(self.runner._belief_state.get("beliefs_state", {}))
                self.state_store.save()
        return last_decision

