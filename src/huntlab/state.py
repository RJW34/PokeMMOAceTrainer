from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from huntlab.config import ScenarioConfig
from huntlab.domain import BeliefState, Observation, Phase


@dataclass
class TemporalReducer:
    config: ScenarioConfig
    window_size: int = 3
    _recent: deque[Observation] = field(default_factory=lambda: deque(maxlen=3))

    def __post_init__(self) -> None:
        self._recent = deque(maxlen=self.window_size)

    def update(self, state: BeliefState, observation: Observation) -> BeliefState:
        if observation.observation_id == state.last_observation_id or observation.stale:
            state.steps_without_progress += 1
            return state

        previous_phase = state.phase
        self._recent.append(observation)
        state.last_observation_id = observation.observation_id

        high_confidence = observation.phase_confidence >= self.config.phase_threshold
        if high_confidence:
            state.phase = observation.phase
            state.phase_confidence = observation.phase_confidence
            state.species = observation.species
            state.species_confidence = observation.species_confidence
            state.shiny_probability = observation.shiny_probability
            state.target_probability = observation.target_probability
            state.current_encounter_id = observation.encounter_id
        else:
            state.phase = Phase.UNKNOWN
            state.phase_confidence = observation.phase_confidence
            state.anomalies.append(
                f"low_phase_confidence:{observation.observation_id}:{observation.phase_confidence:.3f}"
            )

        if observation.phase is Phase.BATTLE and observation.encounter_id:
            if observation.encounter_id not in state.unique_encounter_ids:
                state.unique_encounter_ids.add(observation.encounter_id)
                state.encounters += 1
                if (
                    observation.species
                    and observation.species.lower() in self.config.target_species
                    and observation.target_probability >= self.config.target_threshold
                ):
                    state.target_encounters += 1

        if state.phase != previous_phase:
            state.steps_without_progress = 0
        else:
            state.steps_without_progress += 1

        self._check_contradictions(state)
        return state

    def _check_contradictions(self, state: BeliefState) -> None:
        if len(self._recent) < 2:
            return
        a, b = self._recent[-2], self._recent[-1]
        if (
            a.phase_confidence >= 0.95
            and b.phase_confidence >= 0.95
            and a.observation_id != b.observation_id
            and a.phase is Phase.BATTLE
            and b.phase is Phase.OVERWORLD
            and a.encounter_id == b.encounter_id
            and a.encounter_id is not None
        ):
            state.anomalies.append(f"contradictory_phase_for_encounter:{a.encounter_id}")
            state.phase = Phase.UNKNOWN
            state.phase_confidence = min(a.phase_confidence, b.phase_confidence)
