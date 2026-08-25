import pytest

from huntlab.domain import ActionProposal, BeliefState, Phase, ProposalKind
from huntlab.invariants import InvariantViolation, validate_proposal


def test_unknown_cannot_emit_irreversible_proposal() -> None:
    state = BeliefState(phase=Phase.UNKNOWN)
    proposal = ActionProposal(
        proposal_id="bad",
        kind=ProposalKind.RECOMMEND_CAST,
        reason="bad test proposal",
        confidence=1.0,
    )
    with pytest.raises(InvariantViolation):
        validate_proposal(state, proposal)
