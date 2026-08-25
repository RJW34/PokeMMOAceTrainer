"""Tests for the live-control capability guard.

Every forbidden specimen is assembled from fragments at runtime. If the literals appeared in this
file's source the guard would flag its own test suite, and the usual fix -- exempting a path from
the scan -- would leave a hole that any file could hide behind. Assembling keeps the guard
exclusion-free.
"""

from pathlib import Path

from huntlab.guards.no_live_control import scan, scannable_source

# Specimens, split so this file stays guard-clean. The names are deliberately abbreviated:
# an identifier spelling a forbidden token would itself trip the scan.
GUI_LIB = "pya" + "utogui"
SYNTH_FN = "Send" + "Input"
KEY_EV = "keybd" + "_event"
MOUSE_EV = "mouse" + "_event"
FOCUS_FN = "SetFore" + "groundWindow"
POST_MSG = "Post" + "Message"
X_TOOL = "xdo" + "tool"


def test_guard_accepts_repository_source() -> None:
    assert scan(Path("src")) == []


def test_guard_accepts_repository_tests() -> None:
    """The suite must stay clean too, or `make guard` fails on a green tree."""
    assert scan(Path("tests")) == []


def test_guard_rejects_forbidden_import(tmp_path: Path) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text(f"import {GUI_LIB}\n", encoding="utf-8")
    assert scan(tmp_path)


def test_guard_rejects_win32_input_synthesis(tmp_path: Path) -> None:
    """Input synthesis must be caught even though read-only user32 use is allowed."""
    bad = tmp_path / "actuator.py"
    bad.write_text(
        "import ctypes\n"
        "def press():\n"
        f"    ctypes.windll.user32.{SYNTH_FN}(1, None, 0)\n",
        encoding="utf-8",
    )
    findings = scan(tmp_path)
    assert any(SYNTH_FN.lower() in f.lower() for f in findings)


def test_guard_rejects_subprocess_string_arguments(tmp_path: Path) -> None:
    """A capability hidden in an ordinary string literal is still a capability."""
    bad = tmp_path / "sneaky.py"
    bad.write_text(
        "import subprocess\n" f'subprocess.run(["{X_TOOL}", "key", "z"])\n',
        encoding="utf-8",
    )
    findings = scan(tmp_path)
    assert any(X_TOOL in f.lower() for f in findings)


def test_guard_rejects_tokens_containing_punctuation(tmp_path: Path) -> None:
    """Blanking prose must not break tokens that span punctuation."""
    bad = tmp_path / "punct.py"
    bad.write_text(
        "import ctypes\n" f"ctypes.windll.user32.{POST_MSG}(0, 256, 90, 0)\n",
        encoding="utf-8",
    )
    findings = scan(tmp_path)
    assert any(f"{POST_MSG.lower()}(" in f.lower() for f in findings)


def test_guard_allows_documentation_naming_forbidden_apis(tmp_path: Path) -> None:
    """A module may name a forbidden API to document that it does not use it."""
    documented = tmp_path / "reader.py"
    documented.write_text(
        '"""Reads window geometry only.\n'
        "\n"
        f"Does not use {SYNTH_FN}, {KEY_EV}, {MOUSE_EV}, or {FOCUS_FN}.\n"
        '"""\n'
        "\n"
        f"# Deliberately avoids {POST_MSG}W and {GUI_LIB}.\n"
        "def rect() -> tuple[int, int]:\n"
        f'    """Return a size. Never calls {SYNTH_FN}."""\n'
        "    return (0, 0)\n",
        encoding="utf-8",
    )
    assert scan(tmp_path) == []


def test_scannable_source_blanks_prose_but_keeps_code() -> None:
    text = (
        f'"""Module docstring mentioning {SYNTH_FN}."""\n'
        f"# comment mentioning {KEY_EV}\n"
        f'PAYLOAD = "{X_TOOL}"\n'
    )
    scannable = scannable_source(text, ".py").lower()
    assert SYNTH_FN.lower() not in scannable
    assert KEY_EV.lower() not in scannable
    assert X_TOOL in scannable


def test_scannable_source_preserves_layout() -> None:
    """Blanking must preserve line count and length so reported positions stay meaningful."""
    text = f'"""doc {SYNTH_FN}"""\nX = 1  # {KEY_EV}\nY = 2\n'
    scannable = scannable_source(text, ".py")
    assert len(scannable.splitlines()) == len(text.splitlines())
    assert "X = 1" in scannable and "Y = 2" in scannable


def test_scannable_source_passes_through_non_python() -> None:
    text = f"// mentions {SYNTH_FN} in a comment\n"
    assert scannable_source(text, ".ts") == text
