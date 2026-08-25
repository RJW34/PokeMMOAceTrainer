# Roadmap

## Phase 0: Reproducible foundation

- Typed contracts and schema versions.
- Deterministic simulator.
- Replay fixtures.
- Append-only telemetry.
- No-live-control guard.
- Clean CI.

Exit gate: Magikarp fixture and simulator tests pass from a clean checkout.

## Phase 1: Reliable Magikarp vertical slice

- Temporal evidence fusion.
- Independent shiny evidence channels in prerecorded data.
- Bounded recovery and watchdog.
- Failure bundles.
- Batch simulation reports.
- Read-only OBS dashboard.

Exit gate: branch and mutation tests demonstrate fail-closed behavior.

## Phase 2: General fishing scenario

- Scenario manifest compiler.
- Species-target sets.
- Resource models.
- Multiple fishing outcome models.
- Calibration profiles for replay data.

Exit gate: a new fishing scenario requires only a manifest, fixtures, and optional perception calibration—not new control-flow code.

## Phase 3: General encounter laboratory

- Single encounters and hordes.
- Configurable battle/catch recommendation policies.
- Resource restore planning in simulation.
- Route graph interface for authorized offline adapters.

Exit gate: simulator can evaluate policies across thousands of seeded sessions and emit confidence intervals.

## Phase 4: Learning and active evaluation

- Corpus manager.
- Hard-example mining.
- Calibration metrics.
- Model registry and versioned inference adapters.
- Human label-review workflow.

Exit gate: model changes are accepted only when replay metrics improve without safety regressions.

## Phase 5: Devstream integration

- Honest source badges.
- Event timeline.
- Current belief/proposal explanation.
- Failure replay clips.
- Long-run health metrics.

Exit gate: a viewer can distinguish simulation, replay, offline emulator, and manual guidance at all times.
