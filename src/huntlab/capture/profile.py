"""Capture profiles: where the interesting regions are within a client area.

Regions are stored as fractions of the client rectangle rather than pixels, so one profile
survives a resolution change, a DPI change, or a different monitor. A profile is calibrated
against captured frames and then reused.

This module is target-agnostic. It describes geometry, not any particular application.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class FractionalRegion:
    """A rectangle expressed as fractions of a client area, in the range 0..1."""

    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        for name in ("x", "y", "width", "height"):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be within 0..1, got {value}")
        if self.x + self.width > 1.0 + 1e-9:
            raise ValueError("region extends past the right edge")
        if self.y + self.height > 1.0 + 1e-9:
            raise ValueError("region extends past the bottom edge")

    def pixels(self, frame_width: int, frame_height: int) -> tuple[int, int, int, int]:
        """Return (left, top, right, bottom) in pixels, clamped to the frame."""
        left = int(round(self.x * frame_width))
        top = int(round(self.y * frame_height))
        right = min(frame_width, left + max(1, int(round(self.width * frame_width))))
        bottom = min(frame_height, top + max(1, int(round(self.height * frame_height))))
        return left, top, right, bottom

    def crop(self, image: np.ndarray) -> np.ndarray:
        height, width = image.shape[:2]
        left, top, right, bottom = self.pixels(width, height)
        return image[top:bottom, left:right]

    def to_dict(self) -> dict[str, float]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


@dataclass
class CaptureProfile:
    """Named regions plus the geometry they were calibrated against."""

    profile_id: str
    calibrated_width: int
    calibrated_height: int
    regions: dict[str, FractionalRegion] = field(default_factory=dict)
    notes: str = ""
    schema_version: int = 1

    def region(self, name: str) -> FractionalRegion:
        try:
            return self.regions[name]
        except KeyError:
            known = ", ".join(sorted(self.regions)) or "(none)"
            raise KeyError(
                f"profile {self.profile_id!r} has no region {name!r}; has: {known}"
            ) from None

    def crop(self, image: np.ndarray, name: str) -> np.ndarray:
        return self.region(name).crop(image)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "profile_id": self.profile_id,
            "calibrated_width": self.calibrated_width,
            "calibrated_height": self.calibrated_height,
            "notes": self.notes,
            "regions": {name: r.to_dict() for name, r in sorted(self.regions.items())},
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> CaptureProfile:
        version = int(raw.get("schema_version", 0))
        if version != 1:
            raise ValueError(f"unsupported capture profile schema {version}; expected 1")
        return cls(
            profile_id=str(raw["profile_id"]),
            calibrated_width=int(raw["calibrated_width"]),
            calibrated_height=int(raw["calibrated_height"]),
            regions={
                name: FractionalRegion(**values) for name, values in raw.get("regions", {}).items()
            },
            notes=str(raw.get("notes", "")),
            schema_version=version,
        )

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return target

    @classmethod
    def load(cls, path: str | Path) -> CaptureProfile:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
