# Work Log

## 2026-08-24 — Scaffold baseline

Created the simulator/replay-first architecture and validated the initial vertical slice.

Implemented:

- typed observations, belief state, proposals, and session events;
- scenario manifest loading;
- temporal reducer and invariant checks;
- Magikarp fishing policy;
- replay, guidance, and null sinks;
- deterministic fishing simulator;
- JSONL event telemetry;
- read-only overlay endpoint and HTML;
- source-code capability guard;
- fixture and test suite;
- Claude execution mission and handoff documentation.

Validation performed in the packaging environment:

```text
python -m pip install --no-build-isolation -e .   PASS
python -m huntlab.guards.no_live_control .        PASS
pytest -q                                         PASS (8 tests)
python -m compileall -q src tests scripts         PASS
huntlab replay ...                                PASS; 2 encounters, shiny alert, terminal halt
huntlab simulate --seed 7 --max-steps 100         PASS; deterministic trace
python scripts/run_batch.py --runs 25             PASS; report emitted
```

The packaging environment did not contain cached `ruff` or `mypy` distributions and had no package-network access, so those two commands could not be executed here. They are declared in the development extras and CI workflow for execution in a normal connected environment.

## 2026-08-24 — Repository initialization and first real baseline

Context: the scaffold pack was ingested in full (all 54 files read), flattened from
`pokemon_hunt_agent_lab_scaffold/` to the repository root, and placed under git as
`PokeMMOAceTrainer`.

### Baseline, executed rather than assumed

The previous entry recorded `ruff` and `mypy` as unrunnable in the packaging environment. Both were
executed here for the first time, on CPython 3.12.10 under Windows 11:

```text
python -m pip install -e .[dev,overlay]              PASS
python -m huntlab.guards.no_live_control .           PASS
pytest -q                                            PASS (8 tests)
ruff check .                                         FAIL (6 findings)
mypy src                                             FAIL (1 finding)
huntlab simulate --seed 7 --max-steps 100            PASS (100 steps, 14 encounters)
huntlab replay --input fixtures/...jsonl             PASS (shiny_threshold_reached)
python scripts/run_batch.py --runs 25                PASS (mean 32.8 encounters)
```

### Changes made

Both failures were fixed so that CI is green from the first commit:

- `domain.py`: `Phase` and `ProposalKind` converted from `(str, Enum)` to `StrEnum` (ruff `UP042`).
  All call sites already used `.value`, so serialization is unchanged.
- `domain.py`, `engine.py`, `invariants.py`, `state.py`: `UP017`, `UP035`, and import ordering
  applied via `ruff check --fix`.
- `status.py`: `read_status` now rejects a status file whose JSON root is not an object, instead of
  returning `Any` (mypy `no-any-return`). This makes the reader fail closed.

After the changes: `ruff`, `mypy`, `pytest`, and the guard all pass. `replay` and `simulate` return
byte-identical results to the pre-change run, confirming no behavioral regression.

### Assumption recorded

The `StrEnum` conversion changes `str(Phase.OVERWORLD)` from `"Phase.OVERWORLD"` to `"overworld"`.
No call site relies on the old form; every serialization path uses `.value` explicitly. Verified by
inspection of `domain.to_dict`, `cli.py`, `simulator/fishing.py`, and `status.py`.

### Defect found

`TemporalReducer.update` increments `encounters` and `target_encounters` from the raw observation
rather than the accepted belief. A sub-threshold battle frame is correctly rejected into `UNKNOWN`
belief and still counted. Reproduced directly:

```text
phase_confidence=0.25 battle frame
  belief phase      : unknown
  anomalies         : ['low_phase_confidence:lowconf-001:0.250']
  encounters        : 1
  target_encounters : 1
```

Filed as **D1** in `PROGRESS.md`, ranked high: it violates the fail-closed guarantee in success
criterion 3 and corrupts the statistics later phases are measured against. Not fixed in this
session — recorded as the next task so it lands with its regression fixture.

### Progress tracking added

- `PROGRESS.md` — scorecard against all 13 success criteria, the 12-item kickoff queue, roadmap
  gates, and a ranked defect register. Single source of truth.
- `scripts/update_dashboard.py` — parses `PROGRESS.md` and runs a seeded batch, emitting
  `docs/data/progress.json`. The dashboard is derived, never restated, so it cannot drift.
- `docs/index.html` — GitHub Pages dashboard with honest source badges.
- `make batch` and `make dashboard` targets.

### Not verified

`python -m huntlab.overlay.app` has still not been started or probed in any environment. It remains
marked `UNVERIFIED` in `PROGRESS.md` rather than assumed working.
