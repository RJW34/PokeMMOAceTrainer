# Progress Tracker

Single source of truth for what is **actually built and verified** in this repository.

Ground rules, inherited from `CLAUDE.md`:

- An item is `DONE` only when implementation, tests, and reproducible evidence all exist.
- Evidence is labeled by source (`simulator`, `replay`, `fixture`, `offline`, `manual`). No live-client claims.
- Anything not directly executed is marked `UNVERIFIED`, never assumed.

Legend: `DONE` · `PARTIAL` · `TODO` · `BLOCKED`

---

## Verified baseline — 2026-08-24

Environment: Windows 11, CPython 3.12.10, local `.venv`, editable install.

| Command | Result |
| --- | --- |
| `python -m pip install -e .[dev,overlay]` | PASS |
| `python -m huntlab.guards.no_live_control .` | PASS — guard clean |
| `pytest -q` | PASS — 8 passed |
| `ruff check .` | PASS *(6 findings fixed this session)* |
| `mypy src` | PASS — 25 files *(1 finding fixed this session)* |
| `huntlab simulate --seed 7 --max-steps 100` | PASS — 100 steps, 14 encounters, 14 targets, deterministic |
| `huntlab replay --input fixtures/magikarp_normal_then_shiny.jsonl` | PASS — 9 steps, 2 encounters, `shiny_threshold_reached`, terminal halt |
| `python scripts/run_batch.py --runs 25` | PASS — mean 32.8 encounters, 20/25 runs terminated on shiny |
| `python -m huntlab.overlay.app` | PASS — `/status` 200 with live JSON, `/` 200 serving 1998 bytes of HTML |

The scaffold's own `docs/WORK_LOG.md` recorded `ruff` and `mypy` as unrunnable in its packaging
environment. Both were run here for the first time, both failed, and both are now clean.

---

## Definition of success — scorecard

The thirteen release-candidate criteria from `CLAUDE.md`.

| # | Criterion | Status | Evidence / gap |
| --- | --- | --- | --- |
| 1 | Core loop deterministic under a fixed seed | `DONE` | `test_fixed_seed_is_deterministic` |
| 2 | Every proposal carries reason, confidence, preconditions, postconditions, timeout/recovery | `PARTIAL` | Fields exist on `ActionProposal`; most policy branches leave `preconditions` and `expected` empty, and there is **no timeout field at all** |
| 3 | Unknown or contradictory observations fail closed | `PARTIAL` | Invariant blocks irreversible proposals from `UNKNOWN`, but counters still advance on sub-threshold frames — see defect D1 |
| 4 | Shiny implies alert event, proof request, terminal halt | `PARTIAL` | Alert and halt work (replay-verified). **Proof capture is only prose** in `expected_postconditions`; no artifact is requested or written |
| 5 | Normal encounters never take the shiny branch in the labeled corpus | `BLOCKED` | No labeled corpus exists; `corpus/` holds only a README |
| 6 | Scenario behavior data-driven, not copied into scripts | `PARTIAL` | Thresholds, species, and simulator settings load from the manifest, but branch logic is hard-coded in `FishingPolicy`, and `allowed_sources` plus `terminal_conditions` are parsed by nobody |
| 7 | All transitions event-sourced and reconstructable | `PARTIAL` | `JsonlEventStore` appends observation/belief/proposal/sink events; **no reader reconstructs a session from them** |
| 8 | Replays rerun after code changes to detect regressions | `TODO` | No regression runner, and fixtures carry no expected-transition labels to compare against |
| 9 | Read-only API emits phase, counts, confidence, rate, resources, halt reason | `PARTIAL` | Phase, counts, confidence, and halt reason are present. **Missing: encounters-per-hour, resource estimates, last-progress age, warnings** |
| 10 | Tests cover the eleven named failure modes | `PARTIAL` | 8 tests. Untested: no-bite loops, missed hooks, non-target encounters, resource exhaustion, low-confidence frames, contradictory frames, duplicate/stale frames, long stalls |
| 11 | Guard rejects live-control packages and symbols | `DONE` | Guard passes clean; rejection proven by `test_guard_rejects_forbidden_import` |
| 12 | Install, tests, simulation, replay, overlay run from a clean environment | `DONE` | All five verified above, including a live probe of both overlay endpoints |
| 13 | Documentation matches actual behavior | `PARTIAL` | `README.md` describes an OBS HTML view built on the status endpoint; the served page exists but omits the metrics required by criterion 9 |

**Score: 3 DONE · 8 PARTIAL · 1 TODO · 1 BLOCKED**

---

## Missing domain contracts

`CLAUDE.md` requires typed contracts for eleven concepts. Five are absent from `domain.py`:

| Contract | Status |
| --- | --- |
| `Observation`, `EvidenceRef`, `BeliefState`, `ActionProposal`, `SessionEvent` | `DONE` |
| `ExpectedOutcome` | `TODO` |
| `ScenarioManifest` | `TODO` — `ScenarioConfig` is a flat subset that silently drops manifest fields |
| `FailureBundle` | `TODO` |
| `ResourceSnapshot` | `TODO` — no resource model exists anywhere in the tree |
| `HuntStatistics` | `TODO` — rate and interval math do not exist |

---

## Initial implementation queue

The twelve kickoff tasks from `CLAUDE.md`, in order.

- [x] 1. Validate the current Magikarp simulation and replay tests
- [ ] 2. Introduce schema-versioned event serialization *(constant exists and is validated on read; no migration path or rejection test)*
- [ ] 3. Add temporal evidence fusion with configurable thresholds *(the reducer keeps a 3-frame window but **overwrites** belief from the newest frame instead of fusing)*
- [ ] 4. Add invariant checks for impossible phase/action combinations *(4 checks exist; phase-successor legality is unchecked)*
- [ ] 5. Add a watchdog and bounded recovery budget *(step counter and budget exist; no wall-clock timeout, no cancellation token)*
- [ ] 6. Add a failure-bundle writer
- [ ] 7. Add batch simulation with JSON **and Markdown** reports *(JSON only)*
- [ ] 8. Add replay regression output
- [ ] 9. Add read-only overlay HTML and source badge *(HTML and badge exist and were probed live; still missing the required telemetry fields)*
- [ ] 10. Strengthen the no-live-control guard and test it against representative forbidden snippets *(one snippet tested)*
- [ ] 11. Add property tests for the three named invariants *(`hypothesis` is a declared dependency but **no property test exists**)*
- [ ] 12. Update the roadmap from measured gaps *(this document is that update)*

---

## Roadmap phase gates

| Phase | Gate | Status |
| --- | --- | --- |
| 0 — Reproducible foundation | Magikarp fixture and simulator tests pass from a clean checkout | `DONE` — verified above |
| 1 — Reliable Magikarp slice | Branch and mutation tests demonstrate fail-closed behavior | `PARTIAL` — blocked by D1, and no mutation testing exists |
| 2 — General fishing scenario | A new scenario needs only a manifest and fixtures, no control-flow code | `TODO` — blocked by criterion 6 |
| 3 — General encounter lab | Thousands of seeded sessions with confidence intervals | `TODO` — the batch runner emits means, no intervals |
| 4 — Learning and active evaluation | Model changes accepted only on replay-metric improvement | `TODO` — blocked by the missing corpus and regression runner |
| 5 — Devstream integration | Viewer can always distinguish simulation, replay, offline, and manual | `PARTIAL` — the badge exists, the timeline and explanations do not |

---

## Defect register

Ranked by severity. Each needs a regression fixture before it is closed. Every item is tracked as a [GitHub issue](https://github.com/RJW34/PokeMMOAceTrainer/issues) and grouped into a roadmap milestone.

### D1 — Sub-threshold observations still increment encounter counters *(high)* · [#1](https://github.com/RJW34/PokeMMOAceTrainer/issues/1)

`TemporalReducer.update` keys counting off the **raw observation** rather than the accepted belief,
so a frame rejected as low-confidence still advances `encounters` and `target_encounters`.

Directly reproduced on 2026-08-24 with a `phase_confidence=0.25` battle frame:

```text
belief phase      : unknown          <- correctly rejected
anomalies         : ['low_phase_confidence:lowconf-001:0.250']
encounters        : 1                <- counted anyway
target_encounters : 1                <- counted anyway
```

This contradicts success criterion 3 and corrupts every downstream statistic. Counting must move
behind the confidence gate, keyed on accepted belief.

### D2 — Contradiction detection is one hard-coded pair *(medium)* · [#2](https://github.com/RJW34/PokeMMOAceTrainer/issues/2)

`_check_contradictions` only fires for an exact `BATTLE` to `OVERWORLD` pair sharing an
`encounter_id`, both above `0.95`. Every other contradictory sequence passes silently. The check
should be driven by the phase-successor table in `docs/STATE_MACHINE.md`.

### D3 — Policy mutates belief state while deciding *(medium)* · [#3](https://github.com/RJW34/PokeMMOAceTrainer/issues/3)

`FishingPolicy.decide` writes `state.phase`, `state.halted`, `state.halt_reason`, and
`state.recovery_attempts`. A decision layer with side effects cannot be safely re-run against a
replayed event stream, which blocks criterion 7.

### D4 — Manifest fields parsed by nobody *(medium)* · [#4](https://github.com/RJW34/PokeMMOAceTrainer/issues/4)

`allowed_sources` and `terminal_conditions` are declared in `scenarios/magikarp_fishing.yaml` and
required by `docs/SCENARIO_CONTRACT.md`, but `ScenarioConfig.load` ignores both. A scenario can
therefore run against a source it explicitly forbids.

### D5 — No proof artifact on the shiny branch *(medium)* · [#5](https://github.com/RJW34/PokeMMOAceTrainer/issues/5)

Criterion 4 requires a proof request. The shiny proposal only names proof in a text postcondition;
nothing captures or references an artifact, so the terminal branch leaves no evidence behind.

### D6 — Overlay omits required telemetry fields *(low)* · [#6](https://github.com/RJW34/PokeMMOAceTrainer/issues/6)

The server was probed and both endpoints answer `200`, so the transport works. The payload does not:
it lacks the encounters-per-hour, resource-estimate, last-progress-age, and warning fields required
by criterion 9, which is why criterion 9 remains `PARTIAL` while criterion 12 is `DONE`.

---

## Finding: the live client obfuscates its window title after login

Observed directly on 2026-08-24 on this machine, PokeMMO client revision 32920.

At the server-select screen the window title is Latin `PokeMMO`. After login it becomes
`РokеММO`, which renders identically but is a homoglyph substitution:

| Char | Codepoint | Script |
| --- | --- | --- |
| `Р` | U+0420 | Cyrillic capital ER |
| `o` `k` | U+006F U+006B | Latin |
| `е` | U+0435 | Cyrillic small IE |
| `М` `М` | U+041C x2 | Cyrillic capital EM |
| `O` | U+004F | Latin |

Exactly the confusable letters are swapped and the non-confusable ones (`o`, `k`) are left
Latin. That is not corruption; it is a targeted measure that breaks title-based window lookup
while remaining invisible to the player.

**Consequence for this project.** The live read-only observer is discontinued. Defeating the
substitution -- by normalising homoglyphs, matching on process handle, or capturing the full
screen to sidestep the lookup -- would be circumventing an anti-automation control the operator
added deliberately. `CLAUDE.md` prohibits anti-detection logic and the capability guard enforces
it, so no such workaround belongs in this repository.

Nothing else is invalidated. The capture stack, both shiny evidence channels, the adjudicator,
the alert sink, and the engine are target-agnostic: they consume frames and know nothing about
where the frames came from. An offline emulator adapter supplies those frames without any
countermeasure to defeat, and is the path where full automation is in scope.

---

## Next task

Choose a frame source that does not require defeating a countermeasure (see the finding
above), then **fix D1**, with a regression test for the sub-threshold battle frame and a
fixture covering low-confidence and contradictory frames. It is the highest-leverage item: it is a correctness bug in
the fail-closed guarantee, it silently corrupts the statistics every later phase is measured by, and
it blocks the Phase 1 gate.

Then queue items 3, 8, and 11 — evidence fusion, replay regression output, and the property tests —
in that order.
