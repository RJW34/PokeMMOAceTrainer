# Claude Kickoff Prompt

You are starting work inside the Pokémon Hunt Agent Lab repository.

Read `CLAUDE.md`, `README.md`, every file under `docs/`, the scenario manifests, fixtures, source tree, tests, and CI configuration before changing code. Treat `CLAUDE.md` as the governing mission and capability contract.

Your immediate objective is to take the existing Magikarp fishing research slice from scaffold quality to a production-grade, replay- and simulator-validated vertical slice. Do not stop at analysis, TODOs, mocked screenshots, or empty architecture. Run the baseline, inspect failures and omissions, implement the highest-leverage missing pieces, and prove them with tests and reproducible artifacts.

Required first actions:

1. Run the live-control capability guard, complete test suite, replay fixture, deterministic simulation, and batch simulation.
2. Record the exact baseline in `docs/WORK_LOG.md`.
3. Audit the domain schemas, temporal reducer, policy priority, invariants, watchdog, event log, overlay, fixture format, and packaging.
4. Implement schema-versioned events, stronger temporal evidence fusion, impossible-transition checks, bounded recovery, failure bundles, replay regression reports, and an honest OBS-facing status view.
5. Add fixtures and tests for low-confidence frames, contradictory frames, duplicate/stale observations, long no-bite streaks, non-target encounters, resource exhaustion, recovery success, recovery exhaustion, and shiny terminal behavior.
6. Keep policies declarative. Keep the action boundary sealed. Do not add unattended live PokeMMO input, injection, memory/network access, CAPTCHA handling, anti-detection, or ban-evasion behavior.
7. Run guard, tests, lint, type checking, replay, and batch simulation after changes. Fix all regressions that can be fixed in this session.
8. Leave the repository coherent, documented, and directly runnable from a clean checkout.

You own the end-to-end result. Do not ask the user to resolve routine technical choices that repository inspection or a sensible default can answer. Do not report a feature as complete unless its implementation, tests, and evidence all exist. At the end, provide the exact files changed, commands run, observed results, unresolved defects ranked by severity, claims not directly verified, and the next highest-leverage task.
