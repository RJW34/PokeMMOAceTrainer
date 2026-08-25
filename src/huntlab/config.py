from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ScenarioConfig:
    scenario_id: str
    display_name: str
    target_species: frozenset[str]
    phase_threshold: float
    shiny_threshold: float
    target_threshold: float
    max_steps_without_progress: int
    max_recovery_attempts: int
    simulator: dict[str, Any]

    @classmethod
    def load(cls, path: str | Path) -> ScenarioConfig:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        if int(raw.get("schema_version", 0)) != 1:
            raise ValueError("unsupported scenario schema version")
        thresholds = raw["thresholds"]
        recovery = raw["recovery"]
        return cls(
            scenario_id=str(raw["scenario_id"]),
            display_name=str(raw["display_name"]),
            target_species=frozenset(str(x).lower() for x in raw["target_species"]),
            phase_threshold=float(thresholds["phase"]),
            shiny_threshold=float(thresholds["shiny"]),
            target_threshold=float(thresholds["target"]),
            max_steps_without_progress=int(recovery["max_steps_without_progress"]),
            max_recovery_attempts=int(recovery["max_recovery_attempts"]),
            simulator=dict(raw.get("simulator", {})),
        )
