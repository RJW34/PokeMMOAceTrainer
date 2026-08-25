"""Shiny channel and adjudicator tests on synthetic sprites.

These prove the detection logic independently of any captured frame. Calibration against the
live client replaces the synthetic reference; it does not replace these tests.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from huntlab.perception.shiny import (
    ChannelReading,
    PaletteReference,
    SparkleDetector,
    adjudicate,
    palette_channel,
)

RNG = np.random.default_rng(20260825)


def sprite(hue: int, *, size: int = 64, coverage: float = 0.55, noise: int = 6) -> np.ndarray:
    """A synthetic sprite: a saturated blob of one hue on a desaturated background.

    The background is deliberately low-saturation so the channel's saturation floor excludes it,
    mirroring how a battle background is excluded from a real sprite crop.
    """
    hsv = np.zeros((size, size, 3), dtype=np.uint8)
    hsv[:, :, 0] = 90          # background hue, masked out by the saturation floor
    hsv[:, :, 1] = 10          # below saturation_floor=60
    hsv[:, :, 2] = 120

    radius = int(size * np.sqrt(coverage) / 2)
    centre = size // 2
    yy, xx = np.ogrid[:size, :size]
    blob = (yy - centre) ** 2 + (xx - centre) ** 2 <= radius**2

    jitter = RNG.integers(-noise, noise + 1, size=(size, size))
    hsv[:, :, 0] = np.where(blob, np.clip(hue + jitter, 0, 179), hsv[:, :, 0]).astype(np.uint8)
    hsv[:, :, 1] = np.where(blob, 210, hsv[:, :, 1]).astype(np.uint8)
    hsv[:, :, 2] = np.where(blob, 200, hsv[:, :, 2]).astype(np.uint8)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


NORMAL_HUE = 9    # Magikarp red-orange
SHINY_HUE = 28    # Magikarp gold


def normal_reference(samples: int = 12) -> PaletteReference:
    return PaletteReference.from_samples(
        "magikarp", [sprite(NORMAL_HUE) for _ in range(samples)]
    )


def test_reference_builds_from_samples() -> None:
    ref = normal_reference()
    assert ref.sample_count == 12
    assert ref.hue_histogram.sum() > 0.99
    assert abs(int(np.argmax(ref.hue_histogram)) - NORMAL_HUE) <= 3


def test_normal_sprite_scores_low() -> None:
    reading = palette_channel(sprite(NORMAL_HUE), normal_reference())
    assert reading.probability < 0.25, reading.detail


def test_shiny_sprite_scores_high() -> None:
    reading = palette_channel(sprite(SHINY_HUE), normal_reference())
    assert reading.probability > 0.85, reading.detail


def test_normal_and_shiny_are_well_separated() -> None:
    """The gap matters more than either absolute value: it is what a threshold sits in."""
    ref = normal_reference()
    normals = [palette_channel(sprite(NORMAL_HUE), ref).probability for _ in range(15)]
    shinies = [palette_channel(sprite(SHINY_HUE), ref).probability for _ in range(15)]
    assert max(normals) < min(shinies), f"overlap: normal max {max(normals)}, shiny min {min(shinies)}"


def test_palette_abstains_without_calibration() -> None:
    empty = PaletteReference("magikarp", np.zeros(180), sample_count=0)
    reading = palette_channel(sprite(SHINY_HUE), empty)
    assert reading.probability == 0.0
    assert reading.detail.endswith("abstaining")


def test_palette_abstains_on_too_few_sprite_pixels() -> None:
    blank = np.full((64, 64, 3), 40, dtype=np.uint8)  # nothing above the saturation floor
    reading = palette_channel(blank, normal_reference())
    assert reading.probability == 0.0
    assert reading.detail.endswith("abstaining")


def test_sparkle_builds_baseline_before_judging() -> None:
    det = SparkleDetector()
    dim = np.full((32, 32, 3), 30, dtype=np.uint8)
    first = det.observe(dim)
    assert first.probability == 0.0
    assert "baseline" in first.detail


def test_sparkle_fires_on_transient_brightness() -> None:
    det = SparkleDetector()
    dim = np.full((32, 32, 3), 30, dtype=np.uint8)
    for _ in range(6):
        det.observe(dim)

    burst = dim.copy()
    burst[:16, :16] = 255  # a quarter of the crop flashes
    reading = det.observe(burst)
    assert reading.probability > 0.9, reading.detail


def test_sparkle_ignores_steady_brightness() -> None:
    """A bright scene that stays bright is not a sparkle."""
    det = SparkleDetector()
    bright = np.full((32, 32, 3), 250, dtype=np.uint8)
    for _ in range(8):
        det.observe(bright)
    reading = det.observe(bright)
    assert reading.probability < 0.2, reading.detail


def test_adjudicator_compounds_agreeing_channels() -> None:
    ref = normal_reference()
    palette = palette_channel(sprite(SHINY_HUE), ref)

    det = SparkleDetector()
    dim = np.full((32, 32, 3), 30, dtype=np.uint8)
    for _ in range(6):
        det.observe(dim)
    burst = dim.copy()
    burst[:16, :16] = 255
    sparkle = det.observe(burst)

    verdict = adjudicate([palette, sparkle])
    assert verdict.probability >= max(palette.probability, sparkle.probability)
    assert "both channels agree" in verdict.rationale


def test_adjudicator_compounding_is_strict_when_unsaturated() -> None:
    """With neither channel at 1.0, agreement must strictly exceed the strongest channel."""
    partial_palette = ChannelReading("palette", 0.62, 0.62, "partial hue shift")
    partial_sparkle = ChannelReading("sparkle", 0.55, 1.8, "modest brightness excursion")
    verdict = adjudicate([partial_palette, partial_sparkle])
    assert verdict.probability > 0.62
    assert verdict.probability == pytest.approx(1 - (1 - 0.62) * (1 - 0.55))


def test_adjudicator_caps_uncorroborated_sparkle() -> None:
    """Bright effects are not unique to shinies, so sparkle alone must not reach threshold."""
    det = SparkleDetector()
    dim = np.full((32, 32, 3), 30, dtype=np.uint8)
    for _ in range(6):
        det.observe(dim)
    burst = dim.copy()
    burst[:24, :24] = 255
    sparkle = det.observe(burst)

    empty = PaletteReference("magikarp", np.zeros(180), sample_count=0)
    palette = palette_channel(sprite(SHINY_HUE), empty)  # abstains

    verdict = adjudicate([palette, sparkle])
    assert verdict.probability <= 0.6
    assert "uncorroborated" in verdict.rationale


def test_adjudicator_reports_all_abstained() -> None:
    empty = PaletteReference("magikarp", np.zeros(180), sample_count=0)
    verdict = adjudicate([palette_channel(sprite(SHINY_HUE), empty)])
    assert verdict.probability == 0.0
    assert verdict.rationale == "all channels abstained"


def test_normal_encounter_stays_below_scenario_threshold() -> None:
    """Success criterion 5: a normal encounter must never take the shiny branch."""
    ref = normal_reference()
    det = SparkleDetector()
    steady = np.full((32, 32, 3), 60, dtype=np.uint8)
    for _ in range(6):
        det.observe(steady)

    for _ in range(25):
        crop = sprite(NORMAL_HUE)
        verdict = adjudicate([palette_channel(crop, ref), det.observe(steady)])
        assert verdict.probability < 0.98, verdict.rationale


def test_reference_round_trips_through_dict() -> None:
    ref = normal_reference()
    restored = PaletteReference.from_dict(ref.to_dict())
    assert restored.species == ref.species
    assert restored.sample_count == ref.sample_count
    assert np.allclose(restored.hue_histogram, ref.hue_histogram, atol=1e-7)
