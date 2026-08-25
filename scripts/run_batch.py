from __future__ import annotations

import argparse
import json
from pathlib import Path

from huntlab.actions.replay import ReplaySink
from huntlab.config import ScenarioConfig
from huntlab.engine import AgentEngine
from huntlab.perception.fixture import FixturePerceptor
from huntlab.simulator.fishing import FishingSimulator


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="scenarios/magikarp_fishing.yaml")
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--output", default="runs/batch_report.json")
    args = parser.parse_args()

    config = ScenarioConfig.load(args.scenario)
    rows = []
    for seed in range(args.runs):
        sink = ReplaySink()
        engine = AgentEngine(
            session_id=f"batch-{seed}",
            config=config,
            perceptor=FixturePerceptor(),
            sink=sink,
        )
        result = engine.run(FishingSimulator(config, seed=seed), max_steps=10_000)
        rows.append(
            {
                "seed": seed,
                "steps": result.steps,
                "encounters": result.state.encounters,
                "targets": result.state.target_encounters,
                "halted": result.state.halted,
                "halt_reason": result.state.halt_reason,
            }
        )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "scenario": config.scenario_id,
        "runs": len(rows),
        "terminal_shiny_runs": sum(r["halt_reason"] == "shiny_threshold_reached" for r in rows),
        "mean_encounters": sum(r["encounters"] for r in rows) / max(len(rows), 1),
        "results": rows,
    }
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
