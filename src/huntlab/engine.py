from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from itertools import count
from typing import Any

from huntlab.actions.base import ActionSink
from huntlab.config import ScenarioConfig
from huntlab.domain import BeliefState, SessionEvent
from huntlab.invariants import validate_proposal
from huntlab.perception.base import Perceptor
from huntlab.policy import FishingPolicy
from huntlab.state import TemporalReducer
from huntlab.telemetry import JsonlEventStore


@dataclass
class EngineResult:
    state: BeliefState
    steps: int


class AgentEngine:
    def __init__(
        self,
        *,
        session_id: str,
        config: ScenarioConfig,
        perceptor: Perceptor,
        sink: ActionSink,
        event_store: JsonlEventStore | None = None,
    ) -> None:
        self.session_id = session_id
        self.config = config
        self.perceptor = perceptor
        self.sink = sink
        self.event_store = event_store
        self.state = BeliefState()
        self.reducer = TemporalReducer(config)
        self.policy = FishingPolicy(config)
        self._sequence = count(1)

    def _record(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.event_store is None:
            return
        self.event_store.append(
            SessionEvent(
                event_type=event_type,
                session_id=self.session_id,
                sequence=next(self._sequence),
                payload=payload,
            )
        )

    def step(self, raw: Any) -> None:
        observation = self.perceptor.perceive(raw)
        self._record("observation", observation.to_dict())
        self.reducer.update(self.state, observation)
        self._record("belief", self.state.snapshot())
        proposal = self.policy.decide(self.state)
        validate_proposal(self.state, proposal)
        self._record("proposal", proposal.to_dict())
        result = self.sink.submit(proposal, self.state)
        self._record("sink_result", {"accepted": result.accepted, "message": result.message})

    def run(self, source: Iterable[Any], max_steps: int = 10_000) -> EngineResult:
        steps = 0
        for raw in source:
            if steps >= max_steps or self.state.halted:
                break
            self.step(raw)
            steps += 1
        return EngineResult(state=self.state, steps=steps)
