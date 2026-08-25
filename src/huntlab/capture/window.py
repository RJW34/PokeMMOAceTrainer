"""Read-only discovery of an on-screen window's geometry.

This module locates a window so a screen grabber knows which pixels to read. It is strictly
observational: it enumerates windows, reads titles, and reads bounding rectangles. It never
focuses, moves, resizes, closes, or sends anything to a window.

Only these user32 entry points are used, all of which are read-only:

    EnumWindows, IsWindowVisible, GetWindowTextLengthW, GetWindowTextW,
    GetWindowRect, GetClientRect, ClientToScreen

The input-injection entry points on the same DLL (SendInput, keybd_event, mouse_event,
PostMessageW, SendMessageW, SetForegroundWindow, ...) are rejected by
``huntlab.guards.no_live_control`` and must not be introduced here.
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from dataclasses import dataclass


class WindowLookupError(RuntimeError):
    pass


@dataclass(frozen=True)
class WindowInfo:
    """A window's identity and its client area in screen coordinates."""

    handle: int
    title: str
    left: int
    top: int
    width: int
    height: int

    @property
    def region(self) -> dict[str, int]:
        """Bounding box in the shape ``mss`` expects."""
        return {"left": self.left, "top": self.top, "width": self.width, "height": self.height}

    def describe(self) -> str:
        return f"{self.title!r} at {self.width}x{self.height}+{self.left}+{self.top}"


def _require_windows() -> None:
    if sys.platform != "win32":
        raise WindowLookupError(f"window lookup is Windows-only; this platform is {sys.platform}")


def list_windows() -> list[WindowInfo]:
    """Return every visible, titled top-level window."""
    _require_windows()
    user32 = ctypes.windll.user32
    user32.SetProcessDPIAware()

    found: list[WindowInfo] = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def _collect(hwnd: int, _param: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)

        # Prefer the client area: it excludes the title bar and borders, so the captured
        # region is the game surface rather than window chrome.
        client = wintypes.RECT()
        if not user32.GetClientRect(hwnd, ctypes.byref(client)):
            return True
        origin = wintypes.POINT(0, 0)
        if not user32.ClientToScreen(hwnd, ctypes.byref(origin)):
            return True

        width = client.right - client.left
        height = client.bottom - client.top
        if width > 0 and height > 0:
            found.append(
                WindowInfo(
                    handle=int(hwnd),
                    title=buffer.value,
                    left=int(origin.x),
                    top=int(origin.y),
                    width=int(width),
                    height=int(height),
                )
            )
        return True

    user32.EnumWindows(callback_type(_collect), 0)
    return found


def find_window(substring: str, *, minimum_area: int = 200 * 200) -> WindowInfo:
    """Return the largest visible window whose title contains ``substring`` (case-insensitive).

    Raises ``WindowLookupError`` with the available titles when there is no match, so a
    misconfigured capture fails loudly instead of silently reading the wrong pixels.
    """
    needle = substring.casefold()
    candidates = [
        w
        for w in list_windows()
        if needle in w.title.casefold() and w.width * w.height >= minimum_area
    ]
    if not candidates:
        visible = sorted({w.title for w in list_windows() if w.title.strip()})
        listing = "\n  ".join(visible) or "(none)"
        raise WindowLookupError(
            f"no visible window title contains {substring!r}.\nVisible windows:\n  {listing}"
        )
    return max(candidates, key=lambda w: w.width * w.height)
