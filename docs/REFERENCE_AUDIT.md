# Public Project Reference Audit

This audit extracts reusable software-engineering lessons without adopting live-client control, evasion, or client-tampering behavior.

## Manodiestra/open-pokemmo-bot

Observed design:

- Python with PyAutoGUI and OpenCV template matching.
- Fixed-resolution assumptions.
- Time-based sequences and direct key actions.
- Fishing, Safari handling, and a Payday path.
- Images and scenario logic are tightly coupled to imperative functions.

Useful lesson:

- A tiny vertical slice is valuable for proving the basic loop.

Primary limitations:

- Hard-coded timing and coordinates.
- No explicit state model or confidence fusion.
- Minimal testing, recovery, telemetry, or scenario isolation.
- One unexpected screen often terminates or misroutes the loop.

## yzsvdu/RedTrainer

Observed design:

- Java 17 desktop control panel.
- A local client/server socket with JSON-like payloads.
- Auto-walk, fish, catch, battle, custom move order, and party statistics.
- UI and agent process are more separated than in simple scripts.

Useful lessons:

- Separate operator UI from the agent runtime.
- Define typed command/response payloads.
- Reconnect and surface runtime status.

Primary limitations:

- Public-facing feature contracts remain action-centric rather than evidence-centric.
- The architecture still assumes direct online-client automation.
- No visible replay corpus or rigorous uncertainty/recovery contract.

## RyanMazzeu/BOT-POKEMMO

Observed design:

- Java GUI plus a Python image-location helper.
- Configurability for resolution, key bindings, zoom, and machine variance.
- Pixel checks, OCR, global hotkeys, Robot input, and thread management.
- Fishing and horde/XP paths.

Useful lessons:

- Treat machine/UI variance as configuration rather than an afterthought.
- Pause/cancel behavior needs deliberate concurrency design.
- OCR can supplement visual state classification.

Primary limitations:

- Large monolithic application files.
- Mixed languages joined through a subprocess for one recognition primitive.
- Direct action execution and screen inference are interwoven.
- Configuration burden substitutes for calibration and normalized geometry.

## bearkillerPT/pokeMMOFarmBoye

Observed design:

- Python utility class around screen reading, OCR, template matches, movement, screenshots, and notifications.
- Multiple routes and farming modes.
- OpenCV/HSV plus Tesseract for shiny-related text recognition.
- Gotify notifications and rudimentary CAPTCHA-window detection.

Useful lessons:

- Alerts and proof screenshots are first-class product features.
- Multiple perception channels can be combined.
- Shared utilities prevent some duplication across scenarios.

Primary limitations:

- Scenario scripts still encode route and battle details imperatively.
- OCR-centric shiny classification needs calibration and independent corroboration.
- CAPTCHA awareness and ban-risk commentary are out of scope for this lab.
- No replay-first regression framework.

## ArmadaFreeze/pokeplus

Observed design:

- Decompiled/reconstructed C# application.
- Separate namespaces for botting, input, models, processing, views/view-models, capture, search, sound, and Discord.
- Broad claimed feature set, including farming, catching, shiny alerts, multi-account support, resolution adaptation, and detection-evasion behavior.

Useful lessons:

- Layering into model, processing, view, and integration modules is directionally better than a single script.
- A status model, settings model, notification layer, and reusable battle concepts belong in distinct modules.
- Resolution adaptation should be designed into perception.

Primary limitations:

- Decompiled and obfuscated provenance makes correctness and maintainability uncertain.
- Large singleton/global-state patterns and coordinate tables remain brittle.
- Input execution, screen search, business rules, and state mutations are often tightly coupled.
- Detection-evasion, client manipulation, and live automation are excluded from this scaffold.

## luisl12/PokeMMO-Shinny-Hunter

Observed design:

- Very small Python repository with one main script and a single image asset.

Useful lesson:

- A narrow proof can be kept easy to inspect.

Primary limitations:

- Insufficient architecture, evaluation, or documentation for a general system.

## matheusticiano/Mini-Bot-Pokemmo-2.0

Observed design:

- Python, PyAutoGUI, OpenCV, and PySide6.
- Basic start/pause/stop interface.
- Prescriptive party, hotkey, route, and equipment assumptions.

Useful lesson:

- Operators need explicit prerequisites and lifecycle controls.

Primary limitations:

- Scenario behavior depends on a fixed account setup and UI configuration.
- No belief state, replay suite, or portable capability model.

## Synthesis

The next-generation architecture should preserve the useful pieces—vertical slices, typed payloads, operator UI, configurable calibration, multiple perception channels, notifications, and scenario reuse—while replacing direct imperative loops with:

- confidence-aware observations;
- event-sourced belief state;
- declarative proposals;
- bounded recovery;
- replay evaluation;
- scenario manifests;
- deterministic simulation;
- source-honest telemetry;
- a hard capability gate.
