"""Regenerate the GitHub Pages dashboard data from PROGRESS.md and a batch simulation.

PROGRESS.md is the single source of truth for status. This script parses it rather than
restating it, so the published dashboard cannot drift from the tracked document.

Usage:
    python scripts/update_dashboard.py --runs 200
    python scripts/update_dashboard.py --no-simulate    # parse only, skip the batch run
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROGRESS = ROOT / "PROGRESS.md"
OUTPUT = ROOT / "docs" / "data" / "progress.json"

STATUSES = ("DONE", "PARTIAL", "TODO", "BLOCKED")


def _section(text: str, heading: str) -> str:
    """Return the body of a '## heading' section, up to the next '## '."""
    pattern = re.compile(rf"^## {re.escape(heading)}.*?$(.*?)(?=^## |\Z)", re.M | re.S)
    match = pattern.search(text)
    return match.group(1) if match else ""


def _rows(section: str) -> list[list[str]]:
    """Parse a markdown table body into cell lists, skipping header and separator rows."""
    rows: list[list[str]] = []
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|") or set(line) <= set("|- :"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells and cells[0].lower() in {"#", "phase", "command", "contract"}:
            continue
        rows.append(cells)
    return rows


def _status_of(cell: str) -> str:
    for status in STATUSES:
        if f"`{status}`" in cell or cell.strip() == status:
            return status
    if "PASS" in cell:
        return "PASS"
    if "UNVERIFIED" in cell:
        return "UNVERIFIED"
    return "UNKNOWN"


def _strip_md(value: str) -> str:
    value = re.sub(r"\*\*(.+?)\*\*", r"\1", value)
    value = re.sub(r"\*(.+?)\*", r"\1", value)
    value = re.sub(r"`(.+?)`", r"\1", value)
    return value.strip()


def parse_progress(text: str) -> dict[str, Any]:
    baseline = [
        {"command": _strip_md(r[0]), "result": _strip_md(r[1]), "status": _status_of(r[1])}
        for r in _rows(_section(text, "Verified baseline"))
        if len(r) >= 2
    ]

    criteria = [
        {
            "id": r[0],
            "criterion": _strip_md(r[1]),
            "status": _status_of(r[2]),
            "note": _strip_md(r[3]) if len(r) > 3 else "",
        }
        for r in _rows(_section(text, "Definition of success"))
        if len(r) >= 3 and r[0].isdigit()
    ]

    gates = [
        {"phase": _strip_md(r[0]), "gate": _strip_md(r[1]), "status": _status_of(r[2])}
        for r in _rows(_section(text, "Roadmap phase gates"))
        if len(r) >= 3
    ]

    queue = [
        {"done": mark == "x", "task": _strip_md(task)}
        for mark, task in re.findall(
            r"^- \[( |x)\] (.+)$", _section(text, "Initial implementation queue"), re.M
        )
    ]

    defects = [
        {"id": did, "title": _strip_md(title), "severity": severity}
        for did, title, severity in re.findall(
            r"^### (D\d+) — (.+?) \*\((\w+)\)\*", _section(text, "Defect register"), re.M
        )
    ]

    tally = {status: sum(c["status"] == status for c in criteria) for status in STATUSES}

    return {
        "baseline": baseline,
        "criteria": criteria,
        "criteria_tally": tally,
        "gates": gates,
        "queue": queue,
        "queue_done": sum(1 for q in queue if q["done"]),
        "queue_total": len(queue),
        "defects": defects,
    }


def run_batch(runs: int) -> dict[str, Any] | None:
    """Run the seeded batch simulator and return its summary. Source: simulator."""
    report = ROOT / "runs" / "dashboard_batch.json"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_batch.py"),
         "--runs", str(runs), "--output", str(report)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"batch simulation failed:\n{result.stderr}", file=sys.stderr)
        return None
    data = json.loads(report.read_text(encoding="utf-8"))
    rows = data["results"]
    steps = sorted(r["steps"] for r in rows)
    return {
        "source": "simulator",
        "scenario": data["scenario"],
        "runs": data["runs"],
        "mean_encounters": round(data["mean_encounters"], 2),
        "terminal_shiny_runs": data["terminal_shiny_runs"],
        "shiny_termination_rate": round(data["terminal_shiny_runs"] / max(data["runs"], 1), 4),
        "median_steps": steps[len(steps) // 2] if steps else 0,
        "halt_reasons": {
            reason or "none": sum(1 for r in rows if r["halt_reason"] == reason)
            for reason in {r["halt_reason"] for r in rows}
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=200)
    parser.add_argument("--no-simulate", action="store_true")
    parser.add_argument("--generated-at", default="", help="ISO timestamp stamped into the output")
    args = parser.parse_args()

    payload = parse_progress(PROGRESS.read_text(encoding="utf-8"))
    payload["generated_at"] = args.generated_at
    payload["batch"] = None if args.no_simulate else run_batch(args.runs)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    tally = payload["criteria_tally"]
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    print(f"  criteria : {tally} across {len(payload['criteria'])} tracked")
    print(f"  queue    : {payload['queue_done']}/{payload['queue_total']} complete")
    print(f"  defects  : {len(payload['defects'])} open")
    if payload["batch"]:
        print(f"  batch    : {payload['batch']['runs']} seeded runs (source=simulator)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
