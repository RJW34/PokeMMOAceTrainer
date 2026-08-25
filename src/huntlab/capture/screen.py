"""Read-only screen capture: turns a screen region into a stream of frames.

This is an ObservationSource in the engine's sense. It reads pixels and nothing else — there is
no code path here that can affect the captured application.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import mss
import numpy as np

from huntlab.capture.window import WindowInfo, find_window


@dataclass(frozen=True)
class Frame:
    """One captured frame plus the provenance needed to cite it as evidence."""

    index: int
    captured_at: float
    image: np.ndarray  # BGR, shape (height, width, 3)
    source_id: str
    region: dict[str, int]

    @property
    def frame_id(self) -> str:
        return f"{self.source_id}-{self.index:08d}"

    @property
    def size(self) -> tuple[int, int]:
        return self.image.shape[1], self.image.shape[0]

    def save(self, path: str | Path) -> Path:
        """Write the frame to disk as PNG. Used for proof capture and corpus building."""
        import cv2

        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(target), self.image):
            raise OSError(f"could not write frame to {target}")
        return target


@dataclass
class ScreenCaptureSource:
    """Yields frames from a fixed screen region at a bounded rate.

    Iteration is finite by construction: it stops at ``max_frames`` or ``max_seconds``,
    whichever comes first. The engine's watchdog is a second line of defense, not the only one.
    """

    region: dict[str, int]
    source_id: str = "screen"
    fps: float = 4.0
    max_frames: int = 0  # 0 means unbounded by count
    max_seconds: float = 0.0  # 0 means unbounded by time
    _monitor: dict[str, int] = field(init=False, repr=False, default_factory=dict)

    def __post_init__(self) -> None:
        required = {"left", "top", "width", "height"}
        missing = required - set(self.region)
        if missing:
            raise ValueError(f"region is missing keys: {sorted(missing)}")
        if self.region["width"] <= 0 or self.region["height"] <= 0:
            raise ValueError(f"region has non-positive size: {self.region}")
        if self.fps <= 0:
            raise ValueError("fps must be positive")
        self._monitor = {k: int(self.region[k]) for k in ("left", "top", "width", "height")}

    @classmethod
    def for_window(cls, title_substring: str, **kwargs: Any) -> ScreenCaptureSource:
        window: WindowInfo = find_window(title_substring)
        kwargs.setdefault("source_id", "window")
        return cls(region=window.region, **kwargs)

    def grab_one(self) -> Frame:
        """Capture a single frame immediately."""
        with mss.mss() as sct:
            raw = sct.grab(self._monitor)
            image = np.asarray(raw)[:, :, :3].copy()  # BGRA -> BGR
        return Frame(
            index=0,
            captured_at=time.time(),
            image=image,
            source_id=self.source_id,
            region=dict(self._monitor),
        )

    def __iter__(self) -> Iterator[Frame]:
        interval = 1.0 / self.fps
        started = time.monotonic()
        index = 0
        with mss.mss() as sct:
            while True:
                if self.max_frames and index >= self.max_frames:
                    return
                if self.max_seconds and (time.monotonic() - started) >= self.max_seconds:
                    return

                cycle_start = time.monotonic()
                raw = sct.grab(self._monitor)
                image = np.asarray(raw)[:, :, :3].copy()
                index += 1
                yield Frame(
                    index=index,
                    captured_at=time.time(),
                    image=image,
                    source_id=self.source_id,
                    region=dict(self._monitor),
                )

                elapsed = time.monotonic() - cycle_start
                if elapsed < interval:
                    time.sleep(interval - elapsed)
