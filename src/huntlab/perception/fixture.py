from __future__ import annotations

from typing import Any

from huntlab.domain import Observation


class FixturePerceptor:
    """Converts labeled fixture dictionaries into typed observations."""

    def perceive(self, raw: Any) -> Observation:
        if not isinstance(raw, dict):
            raise TypeError("fixture perceptor expects a dictionary")
        return Observation.from_dict(raw)
