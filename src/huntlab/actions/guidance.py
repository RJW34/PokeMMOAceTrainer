from __future__ import annotations

import json
from collections.abc import Callable

from huntlab.actions.base import SinkResult
from huntlab.domain import ActionProposal, BeliefState


class GuidanceSink:
    """Displays recommendations for a human operator; it never sends inputs."""

    def __init__(self, output: Callable[[str], None] = print) -> None:
        self._output = output

    def submit(self, proposal: ActionProposal, state: BeliefState) -> SinkResult:
        self._output(
            json.dumps(
                {
                    "proposal": proposal.to_dict(),
                    "belief": state.snapshot(),
                    "execution": "human_only",
                },
                sort_keys=True,
            )
        )
        return SinkResult(accepted=True, message="recommendation displayed; no input executed")
