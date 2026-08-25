"""Alert sink: makes a human aware of something and preserves proof of it.

This is an ActionSink in the engine's sense, and like every sink in this project it never
touches the observed application. It notifies a person, writes evidence to disk, and returns.
The human decides what to do in the game.
"""

from __future__ import annotations

import json
import platform
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from huntlab.actions.base import SinkResult
from huntlab.domain import ActionProposal, BeliefState, ProposalKind

ALERTING_KINDS = frozenset({ProposalKind.ALERT_SHINY})


def _beep() -> None:
    """Audible alert. Best effort: never let a failed sound break the alert path."""
    try:
        if platform.system() == "Windows":
            import winsound

            for _ in range(3):
                winsound.Beep(1200, 220)
                winsound.Beep(1800, 220)
        else:
            print("\a", end="", flush=True)
    except Exception:  # noqa: BLE001 - an alert must survive a broken audio device
        pass


def _toast(title: str, message: str) -> None:
    """Desktop notification. Best effort, same reasoning as the beep."""
    try:
        if platform.system() == "Windows":
            script = (
                "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications,"
                " ContentType = WindowsRuntime] > $null;"
                "$t = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(0);"
                "$n = $t.GetElementsByTagName('text');"
                f"$n.Item(0).AppendChild($t.CreateTextNode('{title}')) > $null;"
                f"$n.Item(1).AppendChild($t.CreateTextNode('{message}')) > $null;"
                "$toast = [Windows.UI.Notifications.ToastNotification]::new($t);"
                "[Windows.UI.Notifications.ToastNotificationManager]"
                "::CreateToastNotifier('HuntLab').Show($toast);"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True,
                timeout=10,
                check=False,
            )
    except Exception:  # noqa: BLE001
        pass


@dataclass
class AlertSink:
    """Records every proposal; escalates alerting ones to a human with proof on disk.

    ``proof_provider`` returns the evidence to preserve when an alert fires - in the live path
    this is a closure over the most recent captured frame. It is injected rather than imported
    so the sink stays testable without a screen.
    """

    run_dir: Path = field(default_factory=lambda: Path("runs/alerts"))
    proof_provider: Callable[[], Any] | None = None
    sound: bool = True
    notify: bool = True
    output: Callable[[str], None] = print
    proposals: list[ActionProposal] = field(default_factory=list)
    alerts: list[dict[str, Any]] = field(default_factory=list)

    def submit(self, proposal: ActionProposal, state: BeliefState) -> SinkResult:
        self.proposals.append(proposal)
        if proposal.kind not in ALERTING_KINDS:
            return SinkResult(accepted=True, message="proposal recorded; no alert warranted")
        return self._escalate(proposal, state)

    def _escalate(self, proposal: ActionProposal, state: BeliefState) -> SinkResult:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S_%fZ")
        alert_dir = self.run_dir / f"alert-{stamp}"
        alert_dir.mkdir(parents=True, exist_ok=True)

        proof_path: str | None = None
        proof_error: str | None = None
        if self.proof_provider is not None:
            try:
                frame = self.proof_provider()
                if frame is not None:
                    proof_path = str(frame.save(alert_dir / "proof.png"))
            except Exception as exc:  # noqa: BLE001 - proof failure must not swallow the alert
                proof_error = f"{type(exc).__name__}: {exc}"

        record: dict[str, Any] = {
            "alerted_at": datetime.now(UTC).isoformat(),
            "proposal": proposal.to_dict(),
            "belief": state.snapshot(),
            "proof_path": proof_path,
            "proof_error": proof_error,
            "execution": "human_only",
            "note": "Advisory alert. No input was sent to any application.",
        }
        (alert_dir / "alert.json").write_text(
            json.dumps(record, indent=2, sort_keys=True), encoding="utf-8"
        )
        self.alerts.append(record)

        species = state.species or "unknown species"
        headline = f"SHINY {species} - p={state.shiny_probability:.4f}"
        self.output("")
        self.output("=" * 62)
        self.output(f"  {headline}")
        self.output(f"  {proposal.reason}")
        self.output(f"  encounter : {state.current_encounter_id}")
        self.output(f"  proof     : {proof_path or proof_error or 'none captured'}")
        self.output("=" * 62)
        self.output("")

        if self.sound:
            _beep()
        if self.notify:
            _toast("HuntLab: shiny detected", headline)

        return SinkResult(
            accepted=True,
            message=f"operator alerted; proof at {proof_path or 'unavailable'}",
        )
