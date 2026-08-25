from __future__ import annotations

from typing import Any, Protocol

from huntlab.domain import Observation


class Perceptor(Protocol):
    def perceive(self, raw: Any) -> Observation:
        ...
