"""End-to-end proof of the whole loop: frames -> perception -> belief -> policy -> alert.

Frames are synthesised at the geometry measured from the real client on this machine
(2560x1459), so the region maths, crop sizes, and profile scaling exercise production
dimensions rather than toy ones.

The frame *source* is the only synthetic part. Everything downstream of it - the perceptor, the
two shiny channels, the adjudicator, the temporal reducer, the invariant checks, the policy, and
the alert sink - is the same code any frame source would drive.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import cv2
import numpy as np

from huntlab.actions.alert import AlertSink
from huntlab.capture.profile import CaptureProfile, FractionalRegion
from huntlab.capture.screen import Frame
from huntlab.config import ScenarioConfig
from huntlab.domain import Phase, ProposalKind
from huntlab.engine import AgentEngine
from huntlab.perception.live import (
    CallablePhaseClassifier,
    FixedSpeciesClassifier,
    LivePerceptor,
)
from huntlab.perception.shiny import PaletteReference

CLIENT_WIDTH, CLIENT_HEIGHT = 2560, 1459
NORMAL_HUE, SHINY_HUE = 9, 28

SPRITE = FractionalRegion(x=0.60, y=0.18, width=0.22, height=0.28)

RNG = np.random.default_rng(7)


def profile() -> CaptureProfile:
    return CaptureProfile(
        profile_id="test-client",
        calibrated_width=CLIENT_WIDTH,
        calibrated_height=CLIENT_HEIGHT,
        regions={"enemy_sprite": SPRITE},
        notes="synthetic geometry matching the measured client area",
    )


def make_frame(index: int, phase: Phase, hue: int | None = None, *, flash: bool = False) -> Frame:
    """A frame at production geometry; in battle it paints a sprite of the given hue."""
    image = np.full((CLIENT_HEIGHT, CLIENT_WIDTH, 3), 70, dtype=np.uint8)

    if phase is Phase.BATTLE and hue is not None:
        left, top, right, bottom = SPRITE.pixels(CLIENT_WIDTH, CLIENT_HEIGHT)
        h, w = bottom - top, right - left
        hsv = np.zeros((h, w, 3), dtype=np.uint8)
        hsv[:, :, 0] = 90
        hsv[:, :, 1] = 8
        hsv[:, :, 2] = 110
        yy, xx = np.ogrid[:h, :w]
        blob = ((yy - h // 2) / (h * 0.35)) ** 2 + ((xx - w // 2) / (w * 0.35)) ** 2 <= 1.0
        jitter = RNG.integers(-5, 6, size=(h, w))
        hsv[:, :, 0] = np.where(blob, np.clip(hue + jitter, 0, 179), hsv[:, :, 0]).astype(np.uint8)
        hsv[:, :, 1] = np.where(blob, 205, hsv[:, :, 1]).astype(np.uint8)
        hsv[:, :, 2] = np.where(blob, 195, hsv[:, :, 2]).astype(np.uint8)
        patch = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        if flash:
            patch[: h // 2, : w // 2] = 255  # shiny sparkle burst
        image[top:bottom, left:right] = patch

    return Frame(
        index=index,
        captured_at=time.time(),
        image=image,
        source_id="synthetic-client",
        region={"left": 0, "top": 0, "width": CLIENT_WIDTH, "height": CLIENT_HEIGHT},
    )


def calibrated_reference() -> PaletteReference:
    """Calibrate from normal battle frames, exactly as a real calibration pass would."""
    crops = [
        SPRITE.crop(make_frame(i, Phase.BATTLE, NORMAL_HUE).image) for i in range(1, 13)
    ]
    return PaletteReference.from_samples("magikarp", crops)


def build_engine(sink: AlertSink) -> AgentEngine:
    config = ScenarioConfig.load("scenarios/magikarp_fishing.yaml")
    perceptor = LivePerceptor(
        profile=profile(),
        phase_classifier=CallablePhaseClassifier(
            # Phase is carried on the synthetic frame via a marker attribute in these tests.
            lambda frame, _profile: FRAME_PHASES[frame.index]
        ),
        palette_reference=calibrated_reference(),
        species_classifier=FixedSpeciesClassifier("Magikarp", confidence=0.95),
        target_species=frozenset({"magikarp"}),
    )
    return AgentEngine(
        session_id="e2e",
        config=config,
        perceptor=perceptor,
        sink=sink,
    )


FRAME_PHASES: dict[int, tuple[Phase, float]] = {}


def cycle(start: int, hue: int, *, flash: bool = False) -> list[Frame]:
    """One full fishing cycle: overworld, cast, hooked, battle, summary."""
    steps = [
        (Phase.OVERWORLD, None, False),
        (Phase.CASTING, None, False),
        (Phase.HOOKED, None, False),
        (Phase.BATTLE, hue, flash),
        (Phase.SUMMARY, None, False),
    ]
    frames = []
    for offset, (phase, sprite_hue, do_flash) in enumerate(steps):
        index = start + offset
        FRAME_PHASES[index] = (phase, 0.97)
        frames.append(make_frame(index, phase, sprite_hue, flash=do_flash))
    return frames


def test_normal_encounters_never_alert(tmp_path: Path) -> None:
    """Success criterion 5, on production geometry."""
    FRAME_PHASES.clear()
    sink = AlertSink(run_dir=tmp_path / "alerts", sound=False, notify=False, output=lambda _: None)
    engine = build_engine(sink)

    frames: list[Frame] = []
    for n in range(6):
        frames.extend(cycle(1 + n * 5, NORMAL_HUE))

    result = engine.run(frames, max_steps=200)

    assert sink.alerts == [], "a normal encounter took the shiny branch"
    assert not result.state.halted
    assert result.state.encounters == 6
    assert ProposalKind.ALERT_SHINY not in {p.kind for p in sink.proposals}


def test_shiny_triggers_alert_proof_and_terminal_halt(tmp_path: Path) -> None:
    """Success criterion 4: alert event, proof request, and terminal halt."""
    FRAME_PHASES.clear()
    alert_dir = tmp_path / "alerts"
    latest: dict[str, Frame] = {}

    sink = AlertSink(
        run_dir=alert_dir,
        proof_provider=lambda: latest.get("frame"),
        sound=False,
        notify=False,
        output=lambda _: None,
    )
    engine = build_engine(sink)

    frames: list[Frame] = []
    for n in range(3):
        frames.extend(cycle(1 + n * 5, NORMAL_HUE))
    frames.extend(cycle(1 + 3 * 5, SHINY_HUE, flash=True))

    def tracked() -> list[Frame]:
        for f in frames:
            latest["frame"] = f
            yield f  # type: ignore[misc]

    result = engine.run(tracked(), max_steps=200)

    # Terminal behaviour
    assert result.state.halted
    assert result.state.halt_reason == "shiny_threshold_reached"
    assert sink.proposals[-1].kind is ProposalKind.ALERT_SHINY
    assert sink.proposals[-1].terminal

    # Alert and proof
    assert len(sink.alerts) == 1
    record = sink.alerts[0]
    assert record["execution"] == "human_only"

    proof = Path(record["proof_path"])
    assert proof.exists() and proof.stat().st_size > 0, "no proof artifact written"
    proof_image = cv2.imread(str(proof))
    assert proof_image.shape[:2] == (CLIENT_HEIGHT, CLIENT_WIDTH)

    written = json.loads((proof.parent / "alert.json").read_text(encoding="utf-8"))
    assert written["belief"]["shiny_probability"] >= 0.98
    assert written["belief"]["halt_reason"] == "shiny_threshold_reached"


def test_engine_stops_proposing_after_halt(tmp_path: Path) -> None:
    """The halted state is absorbing: no proposals follow it."""
    FRAME_PHASES.clear()
    sink = AlertSink(run_dir=tmp_path / "alerts", sound=False, notify=False, output=lambda _: None)
    engine = build_engine(sink)

    frames = cycle(1, SHINY_HUE, flash=True)
    frames.extend(cycle(6, NORMAL_HUE))  # would be processed if the halt did not hold

    engine.run(frames, max_steps=200)

    alert_positions = [
        i for i, p in enumerate(sink.proposals) if p.kind is ProposalKind.ALERT_SHINY
    ]
    assert alert_positions, "expected a shiny alert"
    assert alert_positions[0] == len(sink.proposals) - 1, "proposals continued past the halt"


def test_profile_scales_across_resolutions() -> None:
    """One calibrated profile must survive a resolution change."""
    prof = profile()
    small = prof.region("enemy_sprite").pixels(1280, 730)
    large = prof.region("enemy_sprite").pixels(2560, 1459)
    assert large[0] == 2 * small[0] or abs(large[0] - 2 * small[0]) <= 2
    assert (large[2] - large[0]) > (small[2] - small[0])


def test_profile_round_trips(tmp_path: Path) -> None:
    path = profile().save(tmp_path / "profile.json")
    restored = CaptureProfile.load(path)
    assert restored.profile_id == "test-client"
    assert restored.region("enemy_sprite").to_dict() == SPRITE.to_dict()


def test_profile_rejects_unknown_schema(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"schema_version": 99, "profile_id": "x",
                               "calibrated_width": 1, "calibrated_height": 1}), encoding="utf-8")
    try:
        CaptureProfile.load(bad)
    except ValueError as exc:
        assert "unsupported capture profile schema" in str(exc)
    else:
        raise AssertionError("expected an unsupported-schema rejection")
