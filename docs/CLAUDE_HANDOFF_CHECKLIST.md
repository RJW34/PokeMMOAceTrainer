# Claude Handoff Checklist

- [ ] Read `CLAUDE.md`, `README.md`, and all files under `docs/`.
- [ ] Run `python -m huntlab.guards.no_live_control .`.
- [ ] Run `pytest` before making changes.
- [ ] Record baseline results in `docs/WORK_LOG.md`.
- [ ] Select one acceptance gap with an end-to-end test.
- [ ] Add or update a fixture for every behavior change.
- [ ] Keep all policies declarative and all sinks non-live.
- [ ] Run guard, lint, type check, tests, simulation, and replay.
- [ ] Inspect the diff for assets, credentials, caches, and boundary violations.
- [ ] Report exact evidence and known limitations.
