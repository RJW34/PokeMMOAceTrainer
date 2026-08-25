from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from huntlab.domain import ActionProposal, BeliefState


@dataclass(frozen=True)
class SinkResult:
    accepted: bool
    message: str


class ActionSink(Protocol):
    def submit(self, proposal: ActionProposal, state: BeliefState) -> SinkResult:
        """Represent a proposal without controlling a live online client."""
        ...
