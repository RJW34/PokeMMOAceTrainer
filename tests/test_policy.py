from huntlab.config import ScenarioConfig
from huntlab.domain import BeliefState, Phase, ProposalKind
from huntlab.policy import FishingPolicy


def config() -> ScenarioConfig:
    return ScenarioConfig.load("scenarios/magikarp_fishing.yaml")


def test_unknown_requests_evidence() -> None:
    state = BeliefState(phase=Phase.UNKNOWN, phase_confidence=0.2)
    proposal = FishingPolicy(config()).decide(state)
    assert proposal.kind is ProposalKind.REQUEST_EVIDENCE


def test_shiny_halts_before_normal_battle_policy() -> None:
    state = BeliefState(
        phase=Phase.BATTLE,
        phase_confidence=0.99,
        species="Magikarp",
        species_confidence=0.99,
        target_probability=0.99,
        shiny_probability=0.999,
    )
    proposal = FishingPolicy(config()).decide(state)
    assert proposal.kind is ProposalKind.ALERT_SHINY
    assert proposal.terminal
    assert state.halted
