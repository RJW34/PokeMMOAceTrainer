# Test Strategy

## Test pyramid

### Unit tests

- serialization and schema validation;
- temporal evidence fusion;
- invariant checks;
- proposal priority;
- counter deduplication;
- retry budgets;
- rate/statistics calculations.

### Property tests

- shiny evidence above threshold always suppresses ordinary proposals;
- unknown state never yields an irreversible proposal;
- halted state is absorbing;
- retry counts are bounded;
- fixed seeds produce identical traces;
- event replay reconstructs the same terminal state.

### Scenario simulation

Run seeded batches covering:

- no-bite streaks;
- normal target encounters;
- non-target encounters;
- shiny encounter;
- stale frames;
- duplicated frames;
- missing frames;
- resource exhaustion;
- contradictory evidence;
- watchdog recovery and terminal halt.

### Replay regression

Each real bug must add a minimal observation trace. The runner compares:

- expected phases;
- expected proposal kinds;
- halt reason;
- counters;
- alerts;
- confidence bounds.

### Guard tests

CI scans Python, Java, C#, Rust, JavaScript, shell, and PowerShell source for disallowed live-control imports and API symbols. The guard is defense in depth, not a substitute for code review.

## Release gates

- full test suite passes;
- no guard findings;
- type checking and linting pass;
- deterministic simulation report checked in or attached;
- no binary game assets or credentials committed;
- documentation and schemas synchronized.
