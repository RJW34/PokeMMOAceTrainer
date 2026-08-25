from __future__ import annotations

import argparse
from pathlib import Path

SOURCE_SUFFIXES = {".py", ".java", ".cs", ".rs", ".js", ".ts", ".ps1", ".sh"}
IGNORE_PARTS = {".git", ".venv", "dist", "build", "node_modules", "__pycache__"}

# These are checked only in executable source, not Markdown documentation.
FORBIDDEN_TOKENS = {
    "pyautogui",
    "pynput",
    "win32api",
    "win32con",
    "sendinput",
    "postmessage(",
    "sendmessage(",
    "robot.keypress",
    "robot.mouse",
    "jnativehook",
    "autohotkey",
    "directinput",
    "xdo_tool",
    "xdotool",
    "uinput",
    "interception driver",
    "readprocessmemory",
    "writeprocessmemory",
    "create_remote_thread",
    "createremotethread",
    "dllinject",
    "packet capture",
    "captcha solver",
}


def scan(root: Path) -> list[str]:
    findings: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        if any(part in IGNORE_PARTS for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for token in FORBIDDEN_TOKENS:
            if token in text:
                findings.append(f"{path.relative_to(root)}: forbidden token {token!r}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Reject live online-client control code")
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    findings = scan(root)
    if findings:
        print("Live-control capability guard failed:")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("Live-control capability guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
