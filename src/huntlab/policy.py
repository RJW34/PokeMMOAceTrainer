from __future__ import annotations

from itertools import count

from huntlab.config import ScenarioConfig
from huntlab.domain import (
    ActionProposal,
    BeliefState,
    Phase,
    ProposalKind,
)


class FishingPolicy:
    def __init__(self, config: ScenarioConfig) -> None:
        self.config = config
        self._ids = count(1)

    def _proposal(
        self,
        kind: ProposalKind,
        reason: str,
        confidence: float,
        *,
        preconditions: tuple[str, ...] = (),
        expected: tuple[str, ...] = (),
        recovery: str = "request a fresh observation",
        terminal: bool = False,
    ) -> ActionProposal:
        return ActionProposal(
            proposal_id=f"proposal-{next(self._ids):06d}",
            kind=kind,
            reason=reason,
            confidence=confidence,
            preconditions=preconditions,
            expected_postconditions=expected,
            recovery=recovery,
            terminal=terminal,
        )

    def decide(self, state: BeliefState) -> ActionProposal:
        if state.halted or state.phase is Phase.HALTED:
            return self._proposal(
                ProposalKind.HALT,
                state.halt_reason or "session already halted",
                1.0,
                terminal=True,
            )

        if state.shiny_probability >= self.config.shiny_threshold:
            state.phase = Phase.SHINY_ALERT
            state.halted = True
            state.halt_reason = "shiny_threshold_reached"
            return self._proposal(
                ProposalKind.ALERT_SHINY,
                "shiny evidence exceeded configured threshold; request proof and stop",
                state.shiny_probability,
                preconditions=("shiny_probability>=threshold",),
                expected=("operator alerted", "proof requested", "session halted"),
                recovery="none; terminal protective branch",
                terminal=True,
            )

        if state.anomalies and state.anomalies[-1].startswith("contradictory"):
            return self._proposal(
                ProposalKind.REQUEST_EVIDENCE,
                f"contradictory evidence: {state.anomalies[-1]}",
                1.0 - min(state.phase_confidence, 0.99),
                expected=("new non-stale observation",),
            )

        if state.steps_without_progress > self.config.max_steps_without_progress:
            if state.recovery_attempts >= self.config.max_recovery_attempts:
                state.halted = True
                state.halt_reason = "recovery_budget_exhausted"
                state.phase = Phase.HALTED
                return self._proposal(
                    ProposalKind.HALT,
                    "watchdog exceeded and recovery budget is exhausted",
                    1.0,
                    terminal=True,
                )
            state.recovery_attempts += 1
            state.phase = Phase.RECOVERY
            return self._proposal(
                ProposalKind.RECOMMEND_RECOVERY,
                "watchdog detected no progress; recommend a bounded recovery step",
                0.9,
                preconditions=("steps_without_progress>limit",),
                expected=("known phase restored",),
                recovery="halt after configured recovery budget",
            )

        if state.phase is Phase.UNKNOWN:
            return self._proposal(
                ProposalKind.REQUEST_EVIDENCE,
                "phase is unknown or below confidence threshold",
                max(0.0, 1.0 - state.phase_confidence),
                expected=("new high-confidence observation",),
            )

        if state.phase is Phase.OVERWORLD:
            return self._proposal(
                ProposalKind.RECOMMEND_CAST,
                "ready state recognized",
                state.phase_confidence,
                preconditions=("phase=overworld", "not halted"),
                expected=("phase=casting|no_bite|hooked",),
            )

        if state.phase is Phase.CASTING:
            return self._proposal(
                ProposalKind.WAIT,
                "cast result is pending",
                state.phase_confidence,
                expected=("phase=no_bite|hooked",),
            )

        if state.phase is Phase.NO_BITE:
            return self._proposal(
                ProposalKind.RECOMMEND_CONFIRM,
                "no-bite result recognized; recommend acknowledging it",
                state.phase_confidence,
                expected=("phase=overworld",),
            )

        if state.phase is Phase.HOOKED:
            return self._proposal(
                ProposalKind.RECOMMEND_CONFIRM,
                "hook transition recognized; recommend advancing to encounter",
                state.phase_confidence,
                expected=("phase=battle",),
            )

        if state.phase is Phase.BATTLE:
            if state.species is None or state.species_confidence < self.config.phase_threshold:
                return self._proposal(
                    ProposalKind.REQUEST_EVIDENCE,
                    "battle recognized but species evidence is insufficient",
                    1.0 - state.species_confidence,
                )
            is_target = (
                state.species.lower() in self.config.target_species
                and state.target_probability >= self.config.target_threshold
            )
            if is_target:
                return self._proposal(
                    ProposalKind.RECOMMEND_CATCH,
                    f"target species {state.species} recognized",
                    min(state.species_confidence, state.target_probability),
                    preconditions=("phase=battle", "shiny_probability<threshold"),
                    expected=("phase=summary|overworld",),
                )
            return self._proposal(
                ProposalKind.RECOMMEND_RUN,
                f"non-target species {state.species} recognized",
                state.species_confidence,
                preconditions=("phase=battle", "shiny_probability<threshold"),
                expected=("phase=overworld",),
            )

        if state.phase is Phase.SUMMARY:
            return self._proposal(
                ProposalKind.RECOMMEND_CONFIRM,
                "encounter summary recognized",
                state.phase_confidence,
                expected=("phase=overworld",),
            )

        if state.phase is Phase.RECOVERY:
            return self._proposal(
                ProposalKind.REQUEST_EVIDENCE,
                "recovery proposal issued; await a fresh known state",
                0.8,
            )

        if state.phase is Phase.SHINY_ALERT:
            state.halted = True
            state.halt_reason = state.halt_reason or "shiny_alert"
            return self._proposal(
                ProposalKind.ALERT_SHINY,
                "shiny alert state is terminal",
                max(state.shiny_probability, self.config.shiny_threshold),
                terminal=True,
            )

        return self._proposal(ProposalKind.WAIT, "no policy branch matched", 0.0)
