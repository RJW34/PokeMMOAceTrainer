# Architecture

## System context

```text
Recorded fixtures / simulator / authorized offline source
                     |
                     v
              ObservationSource
                     |
                     v
             Perceptor Ensemble
                     |
                     v
          Temporal Evidence Buffer
                     |
                     v
              Belief Reducer
                     |
          +----------+----------+
          |                     |
          v                     v
   Invariant Checker      Metrics Reducer
          |
          v
     Hierarchical Policy
          |
          v
       ActionProposal
          |
          v
      Capability Gate
          |
     +----+-------+----------+
     |            |          |
 Simulator    Replay Sink  Guidance Sink
     |            |          |
     +------------+----------+
                  |
                  v
          Append-only Event Log
                  |
        +---------+---------+
        |                   |
   Failure Bundles      Read-only Overlay
```

## Key distinction: proposal versus execution

A policy never calls a keyboard or mouse API. It emits a proposal such as:

```json
{
  "kind": "recommend_cast",
  "reason": "overworld confidence 0.98 and resources available",
  "confidence": 0.94,
  "preconditions": ["phase=overworld", "not halted"],
  "expected": ["phase becomes casting or no_bite within 4 observations"],
  "recovery": "abstain and request a fresh observation"
}
```

A simulator can interpret that proposal. A guidance UI can display it. A replay sink can compare it with an expected label. The core remains testable and portable.

## Temporal evidence

Perception output is noisy. The reducer should preserve several recent observations and update hypotheses rather than replacing state immediately. Recommended rules:

- irreversible branches require multiple independent evidence channels or one highly calibrated channel;
- stale frames do not count as new evidence;
- contradictory high-confidence observations trigger an anomaly state;
- low confidence triggers `ABSTAIN`, not a guessed action;
- every belief field carries provenance.

## Hierarchical policy

The policy stack is ordered:

1. terminal safety policy;
2. anomaly and watchdog policy;
3. resource policy;
4. shiny policy;
5. encounter policy;
6. scenario policy;
7. idle policy.

Higher-priority policies may suppress lower-priority proposals. This prevents ordinary scenario logic from overriding a shiny halt or invariant violation.

## Recovery contracts

Each phase defines:

- expected successor phases;
- maximum observations without progress;
- retry budget;
- safe recovery proposal;
- terminal escalation.

Retries are bounded and visible in telemetry.

## Versioning

Persisted events and scenario manifests include `schema_version`. Readers must reject incompatible versions with a precise error. Migrations should be explicit and tested.

## Pages dashboard

`index.html` is the published progress dashboard. It renders `data/progress.json`, which is
generated from `PROGRESS.md` by `scripts/update_dashboard.py` (`make dashboard`). Do not hand-edit
`data/progress.json`; edit `PROGRESS.md` and regenerate so the page cannot drift from the tracker.
