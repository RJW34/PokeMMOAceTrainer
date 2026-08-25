from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

SCHEMA_VERSION = 1


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class Phase(StrEnum):
    UNKNOWN = "unknown"
    OVERWORLD = "overworld"
    CASTING = "casting"
    NO_BITE = "no_bite"
    HOOKED = "hooked"
    BATTLE = "battle"
    SUMMARY = "summary"
    RECOVERY = "recovery"
    SHINY_ALERT = "shiny_alert"
    HALTED = "halted"


class ProposalKind(StrEnum):
    WAIT = "wait"
    REQUEST_EVIDENCE = "request_evidence"
    RECOMMEND_CAST = "recommend_cast"
    RECOMMEND_CONFIRM = "recommend_confirm"
    RECOMMEND_RUN = "recommend_run"
    RECOMMEND_CATCH = "recommend_catch"
    RECOMMEND_RECOVERY = "recommend_recovery"
    ALERT_SHINY = "alert_shiny"
    HALT = "halt"


IRREVERSIBLE_PROPOSALS = {
    ProposalKind.RECOMMEND_CAST,
    ProposalKind.RECOMMEND_CONFIRM,
    ProposalKind.RECOMMEND_RUN,
    ProposalKind.RECOMMEND_CATCH,
    ProposalKind.RECOMMEND_RECOVERY,
}


@dataclass(frozen=True)
class EvidenceRef:
    source_id: str
    frame_id: str | None = None
    artifact_path: str | None = None
    channel: str = "fixture"
    score: float | None = None


@dataclass(frozen=True)
class Observation:
    observation_id: str
    phase: Phase
    phase_confidence: float
    species: str | None = None
    species_confidence: float = 0.0
    shiny_probability: float = 0.0
    target_probability: float = 0.0
    encounter_id: str | None = None
    stale: bool = False
    tags: tuple[str, ...] = ()
    evidence: tuple[EvidenceRef, ...] = ()
    observed_at: str = field(default_factory=utc_now_iso)
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in (
            "phase_confidence",
            "species_confidence",
            "shiny_probability",
            "target_probability",
        ):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1, got {value}")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(
                f"unsupported observation schema {self.schema_version}; expected {SCHEMA_VERSION}"
            )

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Observation:
        evidence = tuple(EvidenceRef(**item) for item in raw.get("evidence", []))
        return cls(
            observation_id=str(raw["observation_id"]),
            phase=Phase(raw["phase"]),
            phase_confidence=float(raw["phase_confidence"]),
            species=raw.get("species"),
            species_confidence=float(raw.get("species_confidence", 0.0)),
            shiny_probability=float(raw.get("shiny_probability", 0.0)),
            target_probability=float(raw.get("target_probability", 0.0)),
            encounter_id=raw.get("encounter_id"),
            stale=bool(raw.get("stale", False)),
            tags=tuple(raw.get("tags", [])),
            evidence=evidence,
            observed_at=str(raw.get("observed_at", utc_now_iso())),
            schema_version=int(raw.get("schema_version", SCHEMA_VERSION)),
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["phase"] = self.phase.value
        return value


@dataclass
class BeliefState:
    phase: Phase = Phase.UNKNOWN
    phase_confidence: float = 0.0
    species: str | None = None
    species_confidence: float = 0.0
    shiny_probability: float = 0.0
    target_probability: float = 0.0
    current_encounter_id: str | None = None
    unique_encounter_ids: set[str] = field(default_factory=set)
    encounters: int = 0
    target_encounters: int = 0
    steps_without_progress: int = 0
    recovery_attempts: int = 0
    halted: bool = False
    halt_reason: str | None = None
    last_observation_id: str | None = None
    anomalies: list[str] = field(default_factory=list)

    def snapshot(self) -> dict[str, Any]:
        return {
            "phase": self.phase.value,
            "phase_confidence": self.phase_confidence,
            "species": self.species,
            "species_confidence": self.species_confidence,
            "shiny_probability": self.shiny_probability,
            "target_probability": self.target_probability,
            "current_encounter_id": self.current_encounter_id,
            "unique_encounter_ids": sorted(self.unique_encounter_ids),
            "encounters": self.encounters,
            "target_encounters": self.target_encounters,
            "steps_without_progress": self.steps_without_progress,
            "recovery_attempts": self.recovery_attempts,
            "halted": self.halted,
            "halt_reason": self.halt_reason,
            "last_observation_id": self.last_observation_id,
            "anomalies": list(self.anomalies),
        }


@dataclass(frozen=True)
class ActionProposal:
    proposal_id: str
    kind: ProposalKind
    reason: str
    confidence: float
    preconditions: tuple[str, ...] = ()
    expected_postconditions: tuple[str, ...] = ()
    recovery: str = "request a fresh observation"
    terminal: bool = False
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("proposal confidence must be between 0 and 1")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported proposal schema")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["kind"] = self.kind.value
        return value


@dataclass(frozen=True)
class SessionEvent:
    event_type: str
    session_id: str
    sequence: int
    payload: dict[str, Any]
    created_at: str = field(default_factory=utc_now_iso)
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
