from __future__ import annotations

from huntlab.domain import (
    IRREVERSIBLE_PROPOSALS,
    ActionProposal,
    BeliefState,
    Phase,
    ProposalKind,
)


class InvariantViolation(RuntimeError):
    pass


def validate_proposal(state: BeliefState, proposal: ActionProposal) -> None:
    if state.phase is Phase.UNKNOWN and proposal.kind in IRREVERSIBLE_PROPOSALS:
        raise InvariantViolation("unknown state produced an irreversible proposal")
    if state.halted and proposal.kind not in {ProposalKind.HALT, ProposalKind.ALERT_SHINY}:
        raise InvariantViolation("halted state produced a non-terminal proposal")
    if proposal.kind in {ProposalKind.RECOMMEND_RUN, ProposalKind.RECOMMEND_CATCH}:
        if state.phase is not Phase.BATTLE:
            raise InvariantViolation("battle proposal emitted outside battle")
    if state.shiny_probability > 0.0 and proposal.kind is ProposalKind.RECOMMEND_RUN:
        # The configured threshold is checked by policy. This catches obviously conflicting state.
        if state.shiny_probability >= 0.99:
            raise InvariantViolation("near-certain shiny state produced run recommendation")
