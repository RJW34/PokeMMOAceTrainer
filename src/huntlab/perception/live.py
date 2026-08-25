"""Frame-based perceptor: turns captured pixels into typed observations.

Target-agnostic by construction. It consumes a `Frame` and a `CaptureProfile` and has no
knowledge of where the frame came from - a simulator, a recorded corpus, or an offline emulator
adapter all work identically. Swapping the frame source does not change a line of this module.

Phase classification is injected rather than hard-coded, because which pixels indicate "battle"
is a property of a particular client that must be calibrated, not assumed.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np

from huntlab.capture.profile import CaptureProfile
from huntlab.capture.screen import Frame
from huntlab.domain import EvidenceRef, Observation, Phase
from huntlab.perception.shiny import (
    ChannelReading,
    PaletteReference,
    SparkleDetector,
    adjudicate,
    palette_channel,
)


class PhaseClassifier(Protocol):
    """Decides the phase a frame shows, with a confidence.

    Implementations are calibrated against a specific client. Returning a low confidence is
    always preferable to guessing: the reducer fails closed on sub-threshold phases.
    """

    def classify(self, frame: Frame, profile: CaptureProfile) -> tuple[Phase, float]:
        ...


class SpeciesClassifier(Protocol):
    """Identifies the species on screen, with a confidence. May abstain with 0.0."""

    def classify(self, crop: np.ndarray) -> tuple[str | None, float]:
        ...


@dataclass
class FixedSpeciesClassifier:
    """Assumes a single expected species.

    Honest about what it is: for a single-species hunt such as Old Rod Magikarp this is correct
    and cheap, but it cannot detect a non-target encounter. A real classifier replaces it before
    the scenario is considered general.
    """

    species: str
    confidence: float = 0.85

    def classify(self, crop: np.ndarray) -> tuple[str | None, float]:
        if crop.size == 0:
            return None, 0.0
        return self.species, self.confidence


@dataclass
class LivePerceptor:
    """Frame -> Observation, fusing two shiny evidence channels.

    ``sprite_region`` names the profile region holding the opposing sprite. Shiny evidence is
    only gathered in battle: sampling it elsewhere would pollute the sparkle baseline with
    unrelated scene changes.
    """

    profile: CaptureProfile
    phase_classifier: PhaseClassifier
    palette_reference: PaletteReference | None = None
    species_classifier: SpeciesClassifier | None = None
    sparkle: SparkleDetector = field(default_factory=SparkleDetector)
    sprite_region: str = "enemy_sprite"
    target_species: frozenset[str] = frozenset()

    _encounter_index: int = 0
    _in_battle: bool = False

    def _encounter_id(self) -> str:
        return f"live-encounter-{self._encounter_index:06d}"

    def perceive(self, raw: Any) -> Observation:
        if not isinstance(raw, Frame):
            raise TypeError(f"LivePerceptor expects a Frame, got {type(raw).__name__}")
        frame = raw

        phase, phase_confidence = self.phase_classifier.classify(frame, self.profile)

        # Track encounter boundaries so counters key on a stable identifier.
        if phase is Phase.BATTLE and not self._in_battle:
            self._encounter_index += 1
            self._in_battle = True
            self.sparkle.reset()
        elif phase in (Phase.OVERWORLD, Phase.NO_BITE, Phase.SUMMARY):
            self._in_battle = False

        evidence: list[EvidenceRef] = [
            EvidenceRef(
                source_id=frame.source_id,
                frame_id=frame.frame_id,
                channel="phase",
                score=phase_confidence,
            )
        ]

        species: str | None = None
        species_confidence = 0.0
        shiny_probability = 0.0
        target_probability = 0.0
        encounter_id: str | None = None

        if phase is Phase.BATTLE:
            encounter_id = self._encounter_id()
            crop = self.profile.crop(frame.image, self.sprite_region)

            readings: list[ChannelReading] = []
            if self.palette_reference is not None:
                readings.append(palette_channel(crop, self.palette_reference))
            readings.append(self.sparkle.observe(crop))

            verdict = adjudicate(readings)
            shiny_probability = verdict.probability
            for reading in readings:
                evidence.append(
                    EvidenceRef(
                        source_id=frame.source_id,
                        frame_id=frame.frame_id,
                        channel=f"shiny:{reading.channel}",
                        score=reading.probability,
                    )
                )

            if self.species_classifier is not None:
                species, species_confidence = self.species_classifier.classify(crop)
                if species is not None:
                    evidence.append(
                        EvidenceRef(
                            source_id=frame.source_id,
                            frame_id=frame.frame_id,
                            channel="species",
                            score=species_confidence,
                        )
                    )
                    if species.lower() in self.target_species:
                        target_probability = species_confidence

        return Observation(
            observation_id=frame.frame_id,
            phase=phase,
            phase_confidence=float(np.clip(phase_confidence, 0.0, 1.0)),
            species=species,
            species_confidence=float(np.clip(species_confidence, 0.0, 1.0)),
            shiny_probability=float(np.clip(shiny_probability, 0.0, 1.0)),
            target_probability=float(np.clip(target_probability, 0.0, 1.0)),
            encounter_id=encounter_id,
            evidence=tuple(evidence),
        )


@dataclass
class CallablePhaseClassifier:
    """Adapts a plain function into a PhaseClassifier. Useful for tests and calibration work."""

    function: Callable[[Frame, CaptureProfile], tuple[Phase, float]]

    def classify(self, frame: Frame, profile: CaptureProfile) -> tuple[Phase, float]:
        return self.function(frame, profile)
