from __future__ import annotations

import argparse
import ast
import io
import tokenize
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
    # Win32 input synthesis and window manipulation. The capture package reads window
    # geometry from user32, so the read-only subset must stay read-only: these are the
    # entry points that would turn an observer into an actuator.
    "keybd_event",
    "mouse_event",
    "setforegroundwindow",
    "setcursorpos",
    "sendmessagew",
    "postmessagew",
    "sendmessagea",
    "postmessagea",
    "sendkeys",
    "setwindowshookex",
    "registerhotkey",
    # X11 / macOS / cross-platform input synthesis.
    "xtestfakekeyevent",
    "cgeventpost",
    "cgeventcreatekeyboardevent",
    "pydirectinput",
    "keyboard.press",
    "keyboard.write",
    "mouse.click",
}


def _docstring_spans(tree: ast.AST) -> set[tuple[int, int]]:
    """Return (lineno, col_offset) of every docstring expression in the tree."""
    spans: set[tuple[int, int]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
            if isinstance(first.value.value, str):
                spans.add((first.value.lineno, first.value.col_offset))
    return spans


def scannable_source(text: str, suffix: str) -> str:
    """Return the portion of a file that should be scanned for forbidden capability tokens.

    Comments and docstrings are prose: a module may legitimately *name* a forbidden API in order
    to document that it does not use it. Ordinary string literals are still scanned, because a
    subprocess argument such as an X11 input tool is a real capability, not documentation.

    Prose is blanked in place rather than removed, so character adjacency is preserved. Tokens
    that span punctuation must keep matching, and rebuilding the file from tokens would silently
    break them.

    Non-Python sources are returned unchanged; the guard is defense in depth, not a parser suite.
    """
    if suffix != ".py":
        return text
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return text  # unparseable: scan the raw text rather than skipping the file

    docstrings = _docstring_spans(tree)
    lines = text.splitlines(keepends=True)
    grid = [list(line) for line in lines]

    def blank(start: tuple[int, int], end: tuple[int, int]) -> None:
        start_row, start_col = start
        end_row, end_col = end
        for row in range(start_row, end_row + 1):
            if not 1 <= row <= len(grid):
                continue
            chars = grid[row - 1]
            first = start_col if row == start_row else 0
            last = end_col if row == end_row else len(chars)
            for col in range(first, min(last, len(chars))):
                if chars[col] != "\n":
                    chars[col] = " "

    try:
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if token.type == tokenize.COMMENT:
                blank(token.start, token.end)
            elif token.type == tokenize.STRING and token.start in docstrings:
                blank(token.start, token.end)
    except (tokenize.TokenError, IndentationError):
        return text

    return "".join("".join(row) for row in grid)


def scan(root: Path) -> list[str]:
    findings: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        if any(part in IGNORE_PARTS for part in path.parts):
            continue
        raw = path.read_text(encoding="utf-8", errors="ignore")
        text = scannable_source(raw, path.suffix.lower()).lower()
        for token in sorted(FORBIDDEN_TOKENS):
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
