from __future__ import annotations

import random
from collections.abc import Iterator

from huntlab.config import ScenarioConfig
from huntlab.domain import Phase


class FishingSimulator:
    """Seeded observation generator for an offline fishing research scenario."""

    def __init__(self, config: ScenarioConfig, seed: int = 0) -> None:
        self.config = config
        self.random = random.Random(seed)
        self._observation_index = 0
        self._encounter_index = 0

    def _id(self) -> str:
        self._observation_index += 1
        return f"sim-observation-{self._observation_index:06d}"

    def _observation(self, phase: Phase, confidence: float = 0.99, **extra: object) -> dict[str, object]:
        value: dict[str, object] = {
            "schema_version": 1,
            "observation_id": self._id(),
            "phase": phase.value,
            "phase_confidence": confidence,
            "evidence": [
                {
                    "source_id": "fishing-simulator",
                    "frame_id": str(self._observation_index),
                    "channel": "ground_truth",
                    "score": confidence,
                }
            ],
        }
        value.update(extra)
        return value

    def __iter__(self) -> Iterator[dict[str, object]]:
        sim = self.config.simulator
        no_bite_rate = float(sim.get("no_bite_rate", 0.35))
        shiny_rate = float(sim.get("shiny_rate", 0.001))
        target_rate = float(sim.get("target_rate", 0.9))
        max_encounters = int(sim.get("max_encounters", 100))
        ambiguity_rate = float(sim.get("ambiguity_rate", 0.0))

        yield self._observation(Phase.OVERWORLD)
        for _ in range(max_encounters):
            if self.random.random() < ambiguity_rate:
                yield self._observation(Phase.UNKNOWN, confidence=0.25, tags=["synthetic_ambiguity"])
                yield self._observation(Phase.OVERWORLD)

            yield self._observation(Phase.CASTING)
            if self.random.random() < no_bite_rate:
                yield self._observation(Phase.NO_BITE)
                yield self._observation(Phase.OVERWORLD)
                continue

            yield self._observation(Phase.HOOKED)
            self._encounter_index += 1
            encounter_id = f"sim-encounter-{self._encounter_index:06d}"
            is_target = self.random.random() < target_rate
            species = "Magikarp" if is_target else "Goldeen"
            shiny = self.random.random() < shiny_rate
            yield self._observation(
                Phase.BATTLE,
                species=species,
                species_confidence=0.99,
                target_probability=0.99 if is_target else 0.01,
                shiny_probability=0.999 if shiny else 0.001,
                encounter_id=encounter_id,
                tags=["simulated_shiny"] if shiny else [],
            )
            if shiny:
                return
            yield self._observation(Phase.SUMMARY if is_target else Phase.OVERWORLD)
            if is_target:
                yield self._observation(Phase.OVERWORLD)
