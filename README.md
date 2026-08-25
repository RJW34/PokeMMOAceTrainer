# Pokémon Hunt Agent Lab

A production-oriented research scaffold for building, evaluating, and streaming a resilient Pokémon hunting agent **without unattended control of a live online game service**.

The repository separates perception, belief-state estimation, planning, action proposals, telemetry, simulation, replay evaluation, and presentation. The supplied action boundary supports simulators, replay traces, and a manual guidance console. It intentionally contains no live keyboard/mouse driver, process injection, packet manipulation, memory reader, anti-detection logic, or unattended PokeMMO control.

## Why this architecture

The public PokeMMO bot projects reviewed for this scaffold demonstrate useful ideas, but most combine screen recognition, timing, control, recovery, and scenario logic in a single loop. That makes them brittle when the resolution, UI, latency, route, encounter, or party state changes.

This lab instead uses:

- typed observations and declarative action proposals;
- confidence-aware belief state rather than one-frame guesses;
- hierarchical state machines with explicit invariants;
- scenario manifests instead of hard-coded routes;
- deterministic simulators and replay fixtures;
- event-sourced telemetry and reproducible failure bundles;
- a sealed action-sink interface;
- CI checks that reject live-control dependencies;
- an OBS-friendly read-only status API.

## Included reference scenario

`magikarp_fishing` is the first vertical slice. It exercises:

1. ready/overworld recognition;
2. cast proposal;
3. no-bite recovery;
4. hooked encounter transition;
5. species and shiny classification;
6. flee/catch recommendation;
7. resource and encounter accounting;
8. fail-closed behavior when confidence is low;
9. alert, proof capture request, and terminal halt on a shiny.

The included simulator can run thousands of deterministic or seeded sessions without connecting to a game client.

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -e .[dev,overlay]
pytest
huntlab simulate --scenario scenarios/magikarp_fishing.yaml --seed 7 --max-steps 100
huntlab replay --input fixtures/magikarp_normal_then_shiny.jsonl
python -m huntlab.overlay.app
```

Open the overlay API at `http://127.0.0.1:8765/status`. An OBS browser source can consume a future HTML view built on the same read-only endpoint.

## Repository map

```text
src/huntlab/
  domain.py               Typed observations, beliefs, actions, and events
  engine.py               Sense → update → plan → propose → record loop
  policy.py               Scenario-independent and fishing policies
  telemetry.py            JSONL and SQLite-compatible event contracts
  sources.py              Replay and fixture observation sources
  actions/                 Safe action sinks: guidance, replay, null
  perception/              Perceptor contracts and fixture implementation
  simulator/               Deterministic offline environment adapters
  overlay/                 Read-only monitoring API
  guards/                  CI enforcement of the action boundary
scenarios/                 Declarative hunt definitions
fixtures/                  Reproducible observation traces
corpus/                    Reserved for labeled screenshots and clips
docs/                      Architecture, evaluation, roadmap, and source audit
```

## Non-negotiable boundary

A contribution fails review if it:

- sends keyboard, mouse, controller, touch, or window messages to PokeMMO;
- injects code into or reads memory from the live client;
- manipulates network traffic or protocol data;
- implements CAPTCHA handling, behavioral camouflage, ban avoidance, or detection evasion;
- adds a generic driver whose intended use is unattended online-service automation.

Authorized offline emulators, purpose-built simulators, unit-test fakes, prerecorded media, and manual guidance outputs are in scope.

## Reference projects reviewed

- `Manodiestra/open-pokemmo-bot`
- `yzsvdu/RedTrainer`
- `RyanMazzeu/BOT-POKEMMO`
- `bearkillerPT/pokeMMOFarmBoye`
- `ArmadaFreeze/pokeplus`
- `luisl12/PokeMMO-Shinny-Hunter`
- `matheusticiano/Mini-Bot-Pokemmo-2.0`

See `docs/REFERENCE_AUDIT.md` for the architectural lessons extracted from them.
