from __future__ import annotations

from dataclasses import dataclass, field

from huntlab.actions.base import SinkResult
from huntlab.domain import ActionProposal, BeliefState


@dataclass
class ReplaySink:
    proposals: list[ActionProposal] = field(default_factory=list)

    def submit(self, proposal: ActionProposal, state: BeliefState) -> SinkResult:
        self.proposals.append(proposal)
        return SinkResult(accepted=True, message="proposal captured for replay evaluation")
