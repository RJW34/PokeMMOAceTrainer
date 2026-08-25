# Scenario Manifest Contract

A scenario is behavior plus evidence and evaluation—not merely a name.

Required manifest fields:

- schema version;
- scenario ID and display name;
- source modes allowed;
- target species set;
- shiny confidence threshold;
- general phase threshold;
- maximum steps and stall observations;
- retry budgets;
- configurable encounter probabilities for simulation;
- resource model;
- allowed proposal kinds by phase;
- expected terminal conditions;
- fixture and test references.

A scenario is release-ready only when:

- its manifest validates;
- a deterministic simulator run passes;
- at least one replay fixture covers every main branch;
- low-confidence and contradiction cases fail closed;
- telemetry fields are populated;
- its documentation lists assumptions;
- no scenario-specific key, coordinate, or live-client action appears in core code.
