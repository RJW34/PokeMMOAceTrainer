# Magikarp Fishing State Machine

## States

- `UNKNOWN`: insufficient or contradictory evidence.
- `OVERWORLD`: ready for the next manual/simulated cast.
- `CASTING`: cast has been proposed and a result is pending.
- `NO_BITE`: no encounter occurred; return to overworld.
- `HOOKED`: hook prompt/transition observed.
- `BATTLE`: species/shiny evidence is being evaluated.
- `SUMMARY`: catch/encounter completion summary.
- `RECOVERY`: bounded attempt to regain a known state.
- `SHINY_ALERT`: terminal alert branch.
- `HALTED`: no further proposals except status output.

## Core transitions

```text
UNKNOWN --high-confidence overworld--> OVERWORLD
OVERWORLD --recommend_cast-----------> CASTING
CASTING --no_bite--------------------> NO_BITE
NO_BITE --acknowledged---------------> OVERWORLD
CASTING --hooked---------------------> HOOKED
HOOKED --battle----------------------> BATTLE
BATTLE --shiny-----------------------> SHINY_ALERT
SHINY_ALERT --alert/proof requested--> HALTED
BATTLE --normal target---------------> recommend_catch or recommend_run
BATTLE --normal non-target-----------> recommend_run
BATTLE --uncertain-------------------> UNKNOWN
ANY --watchdog exceeded--------------> RECOVERY
RECOVERY --budget exhausted----------> HALTED
```

## Invariants

- `shiny_probability >= threshold` suppresses normal encounter proposals.
- `UNKNOWN` cannot emit catch, flee, cast, or recovery execution; it may emit only wait, request-evidence, or halt.
- `HALTED` is absorbing.
- A proposal requiring a battle is invalid unless battle belief exceeds threshold.
- Counters change once per unique encounter identifier.
- Retries never exceed the scenario manifest.
- A terminal halt always has a machine-readable reason.
