from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

from huntlab.actions.guidance import GuidanceSink
from huntlab.actions.replay import ReplaySink
from huntlab.config import ScenarioConfig
from huntlab.engine import AgentEngine
from huntlab.perception.fixture import FixturePerceptor
from huntlab.simulator.fishing import FishingSimulator
from huntlab.sources import JsonlSource
from huntlab.status import write_status
from huntlab.telemetry import JsonlEventStore


def _run_engine(source: object, config: ScenarioConfig, source_name: str, max_steps: int) -> int:
    session_id = f"{source_name}-{uuid.uuid4().hex[:10]}"
    run_dir = Path("runs") / session_id
    sink = ReplaySink()
    engine = AgentEngine(
        session_id=session_id,
        config=config,
        perceptor=FixturePerceptor(),
        sink=sink,
        event_store=JsonlEventStore(run_dir / "events.jsonl"),
    )
    result = engine.run(source, max_steps=max_steps)  # type: ignore[arg-type]
    last = sink.proposals[-1] if sink.proposals else None
    status = {
        "source": source_name,
        "phase": result.state.phase.value,
        "proposal": last.kind.value if last else "none",
        "confidence": last.confidence if last else 0.0,
        "encounters": result.state.encounters,
        "target_encounters": result.state.target_encounters,
        "halted": result.state.halted,
        "halt_reason": result.state.halt_reason,
        "session_id": session_id,
        "steps": result.steps,
    }
    write_status(run_dir / "status.json", status)
    write_status("runs/latest_status.json", status)
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="huntlab")
    sub = parser.add_subparsers(dest="command", required=True)

    simulate = sub.add_parser("simulate")
    simulate.add_argument("--scenario", required=True)
    simulate.add_argument("--seed", type=int, default=0)
    simulate.add_argument("--max-steps", type=int, default=1000)

    replay = sub.add_parser("replay")
    replay.add_argument("--input", required=True)
    replay.add_argument("--scenario", default="scenarios/magikarp_fishing.yaml")
    replay.add_argument("--max-steps", type=int, default=1000)

    guidance = sub.add_parser("guidance")
    guidance.add_argument("--input", required=True)
    guidance.add_argument("--scenario", default="scenarios/magikarp_fishing.yaml")

    args = parser.parse_args()
    config = ScenarioConfig.load(args.scenario)

    if args.command == "simulate":
        return _run_engine(
            FishingSimulator(config, seed=args.seed), config, "simulator", args.max_steps
        )
    if args.command == "replay":
        return _run_engine(JsonlSource(args.input), config, "replay", args.max_steps)
    if args.command == "guidance":
        session_id = f"guidance-{uuid.uuid4().hex[:10]}"
        engine = AgentEngine(
            session_id=session_id,
            config=config,
            perceptor=FixturePerceptor(),
            sink=GuidanceSink(),
            event_store=JsonlEventStore(Path("runs") / session_id / "events.jsonl"),
        )
        engine.run(JsonlSource(args.input))
        return 0
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
