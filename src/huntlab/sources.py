from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Protocol


class ObservationSource(Protocol):
    def __iter__(self) -> Iterator[Any]:
        ...


class JsonlSource:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def __iter__(self) -> Iterator[dict[str, Any]]:
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                try:
                    yield json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid JSONL at {self.path}:{line_number}") from exc
