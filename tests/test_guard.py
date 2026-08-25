from pathlib import Path

from huntlab.guards.no_live_control import scan


def test_guard_accepts_repository_source() -> None:
    assert scan(Path("src")) == []


def test_guard_rejects_forbidden_import(tmp_path: Path) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text("import " + "pya" + "utogui\n", encoding="utf-8")
    findings = scan(tmp_path)
    assert findings
