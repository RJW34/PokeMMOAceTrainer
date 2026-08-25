"""Shiny evidence channels and their adjudicator.

`CLAUDE.md` forbids making any single channel the sole shiny detector. Two independent channels
are implemented here:

  palette  - the sprite's hue distribution against a calibrated reference for that species.
             A shiny is a recolour, so this is the primary signal. Shiny Magikarp is gold where
             the normal form is red-orange, which is a large, robust hue separation.

  sparkle  - the transient bright particle burst played when a shiny appears. This is temporal
             rather than chromatic, so it fails independently of the palette channel: a palette
             miss caused by an unusual background does not also suppress the sparkle.

The adjudicator fuses them. It is deliberately conservative about the *absence* of evidence and
generous about corroboration, because the cost of a missed shiny is high and the cost of a
false alert is one wasted human glance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np


@dataclass(frozen=True)
class ChannelReading:
    """One channel's opinion, with the numbers that produced it."""

    channel: str
    probability: float
    score: float
    detail: str

    def as_evidence(self) -> dict[str, object]:
        return {
            "channel": self.channel,
            "score": round(self.score, 5),
            "probability": round(self.probability, 5),
            "detail": self.detail,
        }


@dataclass
class PaletteReference:
    """Calibrated hue statistics for a species' normal colouration.

    Built from captured normal encounters via :meth:`from_samples`, so it reflects the user's
    client, resolution, and rendering rather than assumed sprite values.
    """

    species: str
    hue_histogram: np.ndarray  # normalised, 180 bins (OpenCV hue range)
    sample_count: int = 0
    saturation_floor: int = 60
    value_floor: int = 50

    @staticmethod
    def _masked_hues(bgr: np.ndarray, saturation_floor: int, value_floor: int) -> np.ndarray:
        """Hues of pixels saturated and bright enough to be sprite body, not background."""
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        mask = (hsv[:, :, 1] >= saturation_floor) & (hsv[:, :, 2] >= value_floor)
        return hsv[:, :, 0][mask]

    @classmethod
    def from_samples(
        cls,
        species: str,
        crops: list[np.ndarray],
        *,
        saturation_floor: int = 60,
        value_floor: int = 50,
    ) -> PaletteReference:
        histogram = np.zeros(180, dtype=np.float64)
        used = 0
        for crop in crops:
            hues = cls._masked_hues(crop, saturation_floor, value_floor)
            if hues.size == 0:
                continue
            histogram += np.bincount(hues, minlength=180).astype(np.float64)
            used += 1
        total = histogram.sum()
        if total > 0:
            histogram /= total
        return cls(
            species=species,
            hue_histogram=histogram,
            sample_count=used,
            saturation_floor=saturation_floor,
            value_floor=value_floor,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "species": self.species,
            "sample_count": self.sample_count,
            "saturation_floor": self.saturation_floor,
            "value_floor": self.value_floor,
            "hue_histogram": [round(float(v), 8) for v in self.hue_histogram],
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> PaletteReference:
        return cls(
            species=str(raw["species"]),
            hue_histogram=np.asarray(raw["hue_histogram"], dtype=np.float64),
            sample_count=int(raw.get("sample_count", 0)),
            saturation_floor=int(raw.get("saturation_floor", 60)),
            value_floor=int(raw.get("value_floor", 50)),
        )


def _circular_hue_distance(a: float, b: float) -> float:
    """Distance on the 180-point OpenCV hue circle."""
    raw = abs(a - b) % 180.0
    return min(raw, 180.0 - raw)


def _dominant_hue(histogram: np.ndarray) -> float:
    """Circular mean of a hue histogram.

    ``argmax`` is tempting but fragile: real sprites are multi-modal (Magikarp has a red body,
    yellow fins, and a pale belly), so the tallest bin flips between them under ordinary noise
    and the reported hue jumps with it. The circular mean is stable under that noise and still
    moves decisively when the whole palette shifts, which is exactly the shiny signal.
    """
    total = histogram.sum()
    if total <= 0:
        return -1.0
    # Hue occupies 180 bins covering the full colour circle, hence the 2*pi/180 scaling.
    angles = np.arange(180, dtype=np.float64) * (2.0 * np.pi / 180.0)
    weights = histogram / total
    x = float(np.sum(weights * np.cos(angles)))
    y = float(np.sum(weights * np.sin(angles)))
    if abs(x) < 1e-12 and abs(y) < 1e-12:
        return -1.0
    mean_angle = np.arctan2(y, x) % (2.0 * np.pi)
    return float(mean_angle * (180.0 / (2.0 * np.pi)))


def palette_channel(
    crop: np.ndarray,
    reference: PaletteReference,
    *,
    full_separation_hue: float = 12.0,
) -> ChannelReading:
    """Compare a sprite crop's hue distribution against the species' normal reference.

    ``full_separation_hue`` is the hue distance treated as unambiguous recolouring. Magikarp's
    normal red-orange sits near hue 8-12 and its shiny gold near 25-30, so a 12-point shift is a
    conservative full-confidence threshold.
    """
    if reference.sample_count == 0 or reference.hue_histogram.sum() == 0:
        return ChannelReading("palette", 0.0, 0.0, "no calibration samples; abstaining")

    hues = PaletteReference._masked_hues(crop, reference.saturation_floor, reference.value_floor)
    if hues.size < 25:
        return ChannelReading(
            "palette", 0.0, 0.0, f"only {int(hues.size)} sprite pixels; abstaining"
        )

    observed = np.bincount(hues, minlength=180).astype(np.float64)
    observed /= observed.sum()

    reference_hue = _dominant_hue(reference.hue_histogram)
    observed_hue = _dominant_hue(observed)
    shift = _circular_hue_distance(observed_hue, reference_hue)

    # Bhattacharyya distance corroborates the peak shift with whole-distribution disagreement,
    # so a sprite that merely shifts its brightest pixels does not score as a recolour.
    overlap = float(np.sum(np.sqrt(observed * reference.hue_histogram)))
    divergence = float(np.clip(1.0 - overlap, 0.0, 1.0))

    shift_score = float(np.clip(shift / full_separation_hue, 0.0, 1.0))
    score = 0.6 * shift_score + 0.4 * divergence
    return ChannelReading(
        channel="palette",
        probability=float(np.clip(score, 0.0, 1.0)),
        score=score,
        detail=(
            f"hue {observed_hue:.0f} vs reference {reference_hue:.0f} "
            f"(shift {shift:.1f}, divergence {divergence:.2f}, {int(hues.size)}px)"
        ),
    )


@dataclass
class SparkleDetector:
    """Detects the transient bright burst that accompanies a shiny appearing.

    Keeps a short rolling baseline of the sprite region's brightness. A shiny sparkle is a sharp
    positive excursion in bright-pixel count that decays within roughly a second, which is
    distinguishable from a scene change that raises brightness and keeps it raised.
    """

    window: int = 8
    brightness_threshold: int = 225
    trigger_ratio: float = 2.5
    _history: list[float] = field(default_factory=list)

    def reset(self) -> None:
        self._history.clear()

    @staticmethod
    def _bright_fraction(crop: np.ndarray, threshold: int) -> float:
        grey = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        return float(np.count_nonzero(grey >= threshold)) / float(grey.size or 1)

    def observe(self, crop: np.ndarray) -> ChannelReading:
        current = self._bright_fraction(crop, self.brightness_threshold)
        baseline_samples = self._history[-self.window :]
        self._history.append(current)
        if len(self._history) > self.window * 4:
            del self._history[: -self.window * 2]

        if len(baseline_samples) < 3:
            return ChannelReading(
                "sparkle", 0.0, current, f"building baseline ({len(baseline_samples)}/3)"
            )

        baseline = float(np.median(baseline_samples))
        # Floor the baseline so a dark sprite region cannot produce an absurd ratio from
        # a handful of pixels; 0.002 is well below any real sparkle burst.
        floor = 0.002
        ratio = max(current, 0.0) / max(baseline, floor)
        score = float(np.clip((ratio - 1.0) / (self.trigger_ratio - 1.0), 0.0, 1.0))
        return ChannelReading(
            channel="sparkle",
            probability=score,
            score=ratio,
            detail=f"bright fraction {current:.4f} vs baseline {baseline:.4f} (x{ratio:.2f})",
        )


@dataclass(frozen=True)
class ShinyVerdict:
    probability: float
    readings: tuple[ChannelReading, ...]
    rationale: str

    @property
    def channels(self) -> dict[str, float]:
        return {r.channel: r.probability for r in self.readings}


def adjudicate(readings: list[ChannelReading]) -> ShinyVerdict:
    """Fuse channel readings into one shiny probability.

    Rules, in the spirit of `docs/ARCHITECTURE.md`:

    - Corroboration beats any single channel: two channels in agreement exceed either alone.
    - A single strong palette reading can still carry the verdict, because the sparkle is a
      brief animation that a 4fps capture can miss entirely. Missing a shiny is the expensive
      error; a false alert costs one human glance.
    - An abstaining channel contributes nothing rather than dragging the result toward zero.
    """
    active = [r for r in readings if not r.detail.endswith("abstaining")]
    if not active:
        return ShinyVerdict(0.0, tuple(readings), "all channels abstained")

    palette = next((r for r in active if r.channel == "palette"), None)
    sparkle = next((r for r in active if r.channel == "sparkle"), None)

    if palette and sparkle and palette.probability > 0.4 and sparkle.probability > 0.4:
        # Noisy-OR: independent channels agreeing compound toward certainty.
        fused = 1.0 - (1.0 - palette.probability) * (1.0 - sparkle.probability)
        return ShinyVerdict(
            float(np.clip(fused, 0.0, 1.0)),
            tuple(readings),
            f"both channels agree (palette {palette.probability:.2f}, "
            f"sparkle {sparkle.probability:.2f})",
        )

    strongest = max(active, key=lambda r: r.probability)
    if strongest.channel == "palette":
        return ShinyVerdict(
            strongest.probability,
            tuple(readings),
            f"palette alone: {strongest.detail}",
        )

    # Sparkle without palette corroboration is capped: bright effects are not unique to shinies.
    return ShinyVerdict(
        float(min(strongest.probability, 0.6)),
        tuple(readings),
        f"sparkle uncorroborated, capped: {strongest.detail}",
    )
