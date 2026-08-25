from __future__ import annotations

from huntlab.actions.base import SinkResult
from huntlab.domain import ActionProposal, BeliefState


class NullSink:
    def submit(self, proposal: ActionProposal, state: BeliefState) -> SinkResult:
        return SinkResult(accepted=True, message="proposal intentionally discarded")
