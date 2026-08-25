from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_STATUS: dict[str, Any] = {
    "source": "none",
    "phase": "unknown",
    "proposal": "none",
    "confidence": 0.0,
    "encounters": 0,
    "target_encounters": 0,
    "halted": False,
    "halt_reason": None,
}


def write_status(path: str | Path, value: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".tmp")
    temp.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    temp.replace(target)


def read_status(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    if not target.exists():
        return dict(DEFAULT_STATUS)
    loaded = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"status file {target} does not contain a JSON object")
    return loaded
