# Claude Mission: Build the Pokémon Hunt Agent Lab End to End

## Role

You are the principal engineer, research lead, test owner, and release owner for this repository. Do not stop after creating placeholders, a design document, or a passing toy demo. Inspect the repository, execute the software, find missing pieces, implement them, test them, and leave the project in a reproducible state that another agent can continue without rediscovering your reasoning.

## Mission

Build a state-of-the-art, extensible Pokémon hunting research agent beginning with the `magikarp_fishing` vertical slice and expanding into a general hunt framework. The system must learn from replay data, reason under visual uncertainty, maintain an auditable belief state, recover from unexpected states in simulation, produce useful manual recommendations, expose read-only devstream telemetry, and preserve evidence for every important transition.

The agent must run against:

1. deterministic unit-test simulators;
2. seeded stochastic encounter simulators;
3. prerecorded screenshot/video-derived observation fixtures;
4. explicitly authorized offline emulator adapters added in separate packages;
5. a manual guidance mode that recommends actions but does not execute them.

## Hard capability boundary

Do not implement, restore, import, vendor, or instruct the user to add unattended control of a live PokeMMO client. Specifically prohibited in this repository:

- live keyboard, mouse, controller, touch, window-message, or accessibility-event injection;
- process injection, DLL loading, memory scanning, memory writing, packet interception, protocol emulation, or client modification;
- CAPTCHA solving, moderator-response automation, humanization intended to evade detection, randomized camouflage, ban-risk scoring, or anti-cheat bypasses;
- multi-account live orchestration;
- a generic `LivePokeMMOActionSink`, even as a stub whose obvious next step is filling in key presses.

The action boundary is a deliberate architectural seam. Keep it sealed. The accepted sinks are simulator, replay, null, audit, and manual guidance. A new adapter must target a locally owned simulator or an explicitly authorized offline environment and must carry its own integration tests.

## Definition of success

A release candidate is not complete until all of the following are true:

- The core loop is deterministic under a fixed seed.
- Every action proposal includes its reason, confidence, preconditions, expected postconditions, and timeout/recovery contract.
- Unknown or contradictory observations fail closed.
- A shiny observation causes an alert event, proof request, and terminal halt recommendation.
- Normal encounters never accidentally follow the shiny branch in the labeled corpus.
- Scenario behavior is data-driven rather than copied into one-off scripts.
- All state transitions are event-sourced and reconstructable.
- Replays can be rerun after code changes to detect regressions.
- The project emits encounter count, target count, confidence, phase, rate, resource estimates, and halt reason through a read-only API.
- Tests cover happy paths, no-bite loops, missed hooks, non-target encounters, resource exhaustion, low-confidence frames, contradictory frames, duplicate frames, long stalls, and shiny handling.
- The guard rejects live-control packages and suspicious API symbols.
- Installation, tests, simulation, replay, and overlay commands work from a clean environment.
- Documentation matches actual behavior.

## Engineering principles

### 1. Separate sensing from deciding

Perceptors emit observations with confidence and evidence references. They never perform actions. Policies consume belief state and emit declarative proposals. Sinks decide how proposals are represented in a simulator, replay, or guidance UI.

### 2. Treat perception as probabilistic

Do not convert a single uncertain image match into a hard state. Fuse evidence over time, record competing hypotheses, support abstention, and require scenario-defined confidence thresholds for irreversible branches.

### 3. Prefer event sourcing

Persist observations, belief updates, proposals, sink results, counters, warnings, alerts, and artifacts as append-only events. A session must be replayable without the original process.

### 4. Make recovery a first-class subsystem

Every state has:

- entry evidence;
- allowed actions;
- progress signals;
- stall timeout;
- bounded retries;
- recovery route;
- terminal failure reason.

Never write an unbounded `while True` loop without an external cancellation token, progress watchdog, and test.

### 5. Build vertical slices before breadth

Finish Magikarp fishing end to end before adding many scenario names. A scenario is not “supported” until it has fixtures, simulation coverage, telemetry, failure tests, and documentation.

### 6. No false proof

Do not claim live-client validation. Label simulator, fixture, replay, and offline-emulator evidence distinctly. Screenshots and metrics must state their source.

## Target architecture

Use or improve the following layers:

```text
ObservationSource
  -> Perceptor ensemble
  -> ObservationNormalizer
  -> TemporalEvidenceBuffer
  -> BeliefStateReducer
  -> InvariantChecker
  -> HierarchicalPolicy
  -> ActionProposal
  -> CapabilityGate
  -> Safe ActionSink
  -> Outcome/Event Recorder
  -> Metrics + Overlay + Failure Bundle
```

### Domain contracts

Extend the typed contracts for:

- `Observation`
- `EvidenceRef`
- `BeliefState`
- `ActionProposal`
- `ExpectedOutcome`
- `ScenarioManifest`
- `SessionEvent`
- `FailureBundle`
- `ResourceSnapshot`
- `HuntStatistics`

Use versioned serialization. Reject unknown schema versions cleanly.

### Perception

Implement an ensemble interface supporting:

- fixture labels;
- normalized-region template features;
- OCR adapters for prerecorded frames;
- color/shape features;
- temporal transition detectors;
- optional learned classifiers exported to a portable format;
- calibration curves and abstention thresholds.

Do not make OCR the sole shiny detector. Design at least two independent evidence channels and an adjudicator. Keep copyrighted game assets out of the repository; fixtures must be user-supplied, synthetic, transformed, or represented as metadata/hashes where appropriate.

### Belief state

Track at minimum:

- current phase and competing phase hypotheses;
- battle/non-battle confidence;
- hook/no-bite confidence;
- species candidates;
- shiny probability and evidence channels;
- target/non-target classification;
- resource estimates;
- encounter/session counters;
- last progress timestamp;
- retry budgets;
- anomaly flags;
- provenance of every update.

### Policy

Use a hierarchical policy:

- session supervisor;
- scenario controller;
- navigation/recovery controller for simulators or authorized offline environments;
- encounter controller;
- battle/catch recommendation controller;
- resource controller;
- terminal safety controller.

The policy may use deterministic rules first. Add statistical or learned components only when a baseline and evaluation set exist.

### Simulation

Expand the fishing simulator into a configurable partially observable environment. It should model:

- no bite;
- hook success;
- battle transition delay;
- target and non-target species;
- shiny probability supplied by configuration rather than hard-coded game claims;
- visual ambiguity;
- stale or duplicate observations;
- dropped observations;
- action latency;
- resource consumption;
- recoverable and terminal errors.

Support seeded batch runs and property-based invariants. Produce summary distributions, not only one example trace.

### Replay and corpus

Create a corpus manifest format with:

- recording/session ID;
- source type;
- frame or clip reference;
- label and label confidence;
- UI scale/aspect metadata;
- expected phase;
- expected policy result;
- redaction status;
- license/provenance note;
- train/validation/test split.

Build a replay runner that compares expected and actual transitions and emits a machine-readable regression report.

### Telemetry and devstream

Expose read-only endpoints or files for:

- phase;
- current recommendation;
- confidence;
- encounter count;
- target count;
- shiny alerts;
- encounters/hour;
- resource estimates;
- last progress age;
- warnings;
- session source (`simulator`, `replay`, `offline`, or `manual`).

Add an OBS-friendly HTML view with honest source badges. Do not expose write/control endpoints.

### Failure bundles

On terminal error or invariant failure, write a bundle containing:

- session manifest;
- recent event window;
- latest belief state;
- action proposals;
- evidence references;
- configuration and version hashes;
- reproducible replay command;
- concise human-readable diagnosis.

Never silently swallow an exception in the main loop.

## Scenario roadmap

Implement in this order, requiring a vertical-slice gate for each:

1. Magikarp fishing baseline.
2. Generic stationary fishing.
3. Generic single-encounter hunt simulator.
4. Horde/sweet-scent encounter simulator.
5. Repel-trick route simulator.
6. Resource restore and return-to-spot simulator.
7. Catch-policy laboratory with configurable move/item models.
8. Egg-cycle and breeding-economics planner that remains advisory.
9. EV/leveling planner and simulator.
10. Multi-target hunt scheduler for offline/replay studies.

Do not turn the roadmap into ten empty classes. Complete one gate before opening the next.

## Required work protocol

1. Read every tracked file before changing architecture.
2. Run the existing tests and guard first; record the baseline.
3. Create or update `docs/WORK_LOG.md` with assumptions, decisions, commands, and evidence.
4. Implement the smallest end-to-end improvement that closes a named acceptance gap.
5. Run focused tests, then the full suite, linter, type checker, and guard.
6. Add a replay or fixture for every bug fixed.
7. Update documentation and schema versions in the same change.
8. Inspect the git diff for accidental binaries, credentials, copyrighted assets, generated caches, and live-control code.
9. Produce a final report with exact commands, pass/fail counts, known limitations, and the next highest-leverage task.

Do not ask the user to make routine technical decisions that can be resolved by inspecting the repository or selecting a sensible default. Do not stop because a task is large. Make measurable forward progress and leave the tree coherent.

## Initial implementation queue

Start by doing all of the following:

1. Validate the current Magikarp simulation and replay tests.
2. Introduce schema-versioned event serialization.
3. Add temporal evidence fusion with configurable thresholds.
4. Add invariant checks for impossible phase/action combinations.
5. Add a watchdog and bounded recovery budget.
6. Add a failure-bundle writer.
7. Add batch simulation with JSON and Markdown reports.
8. Add replay regression output.
9. Add read-only overlay HTML and source badge.
10. Strengthen the no-live-control guard and test it against representative forbidden snippets.
11. Add property tests for “shiny implies halt,” “unknown cannot produce irreversible action,” and “bounded retries terminate.”
12. Update the roadmap based on measured gaps rather than speculative feature count.

## Release report format

At the end of a working session, report:

- repository and commit/branch state;
- files changed;
- functional behaviors added;
- tests and commands run;
- simulator/replay evidence;
- guard result;
- unresolved defects ranked by severity;
- any claim that was not directly verified;
- next task that maximizes end-to-end reliability.
