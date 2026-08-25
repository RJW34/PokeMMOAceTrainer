"""Record a read-only capture session from a running game window.

This builds the corpus that perception is calibrated against. It reads pixels and writes PNGs
plus a JSONL manifest. It sends nothing to the captured application.

Usage:
    python scripts/capture_session.py --seconds 180 --fps 4
    python scripts/capture_session.py --list-windows
    python scripts/capture_session.py --window "PokeMMO" --seconds 60 --label overworld_fishing

Output goes to corpus/raw/<session-id>/ which is gitignored: raw game captures are not
committed. Only derived metadata, hashes, and labels belong in version control.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import cv2

from huntlab.capture import ScreenCaptureSource, WindowLookupError, find_window, list_windows

ROOT = Path(__file__).resolve().parents[1]


def _print(text: str) -> None:
    """Print without dying on window titles the console codepage cannot encode."""
    encoding = sys.stdout.encoding or "utf-8"
    sys.stdout.write(text.encode(encoding, errors="replace").decode(encoding) + "\n")
    sys.stdout.flush()


def show_windows() -> int:
    windows = sorted(
        (w for w in list_windows() if w.title.strip()),
        key=lambda w: -(w.width * w.height),
    )
    _print(f"{len(windows)} visible titled windows:\n")
    for w in windows:
        _print(f"  {w.width:>5}x{w.height:<5} +{w.left},{w.top}   {w.title}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window", default="PokeMMO", help="substring of the window title")
    parser.add_argument("--seconds", type=float, default=120.0)
    parser.add_argument("--fps", type=float, default=4.0)
    parser.add_argument("--label", default="unlabeled", help="what you will be doing on camera")
    parser.add_argument("--every", type=int, default=1, help="save every Nth captured frame")
    parser.add_argument("--scale", type=float, default=1.0,
                        help="resize factor before saving; 0.5 quarters the storage")
    parser.add_argument("--jpeg", type=int, default=0, metavar="Q",
                        help="save JPEG at quality Q instead of PNG (1-100); ~10x smaller")
    parser.add_argument("--full-screen", action="store_true",
                        help="capture the whole primary display instead of one window")
    parser.add_argument("--list-windows", action="store_true")
    args = parser.parse_args()

    if args.list_windows:
        return show_windows()

    if args.full_screen:
        import mss

        with mss.mss() as sct:
            monitor = dict(sct.monitors[1])
        region = {k: int(monitor[k]) for k in ("left", "top", "width", "height")}
        title = "<primary display>"
    else:
        try:
            window = find_window(args.window)
        except WindowLookupError as exc:
            _print(str(exc))
            _print("\nIs the client running and not minimized? "
                   "Re-run with --list-windows to see what is visible.")
            return 2
        region = window.region
        title = window.title

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    session_id = f"{args.label}-{stamp}"
    out_dir = ROOT / "corpus" / "raw" / session_id
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    _print(f"window   : {title}")
    _print(f"region   : {region['width']}x{region['height']} at +{region['left']},{region['top']}")
    _print(f"recording: {args.seconds:.0f}s at {args.fps:g} fps, saving every {args.every}")
    _print(f"output   : {out_dir.relative_to(ROOT)}")
    _print("\nGo. Play normally; this only reads the screen.\n")

    source = ScreenCaptureSource(
        region=region,
        source_id=session_id,
        fps=args.fps,
        max_seconds=args.seconds,
    )

    manifest = out_dir / "frames.jsonl"
    saved = 0
    started = time.monotonic()
    with manifest.open("w", encoding="utf-8") as handle:
        for frame in source:
            if frame.index % args.every != 0:
                continue
            image = frame.image
            if args.scale != 1.0:
                image = cv2.resize(
                    image,
                    (max(1, int(image.shape[1] * args.scale)),
                     max(1, int(image.shape[0] * args.scale))),
                    interpolation=cv2.INTER_AREA,
                )
            suffix = "jpg" if args.jpeg else "png"
            path = frames_dir / f"{frame.index:06d}.{suffix}"
            params = [cv2.IMWRITE_JPEG_QUALITY, args.jpeg] if args.jpeg else []
            if not cv2.imwrite(str(path), image, params):
                raise OSError(f"could not write frame to {path}")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            handle.write(json.dumps({
                "session_id": session_id,
                "index": frame.index,
                "captured_at": frame.captured_at,
                "elapsed": round(frame.captured_at - source_start(started), 3),
                "path": str(path.relative_to(out_dir)).replace("\\", "/"),
                "sha256": digest,
                "width": int(image.shape[1]),
                "height": int(image.shape[0]),
                "capture_width": frame.size[0],
                "capture_height": frame.size[1],
                "scale": args.scale,
                "region": frame.region,
                "label": args.label,
                "source_mode": "live_capture_readonly",
            }, sort_keys=True) + "\n")
            saved += 1
            if saved % 20 == 0:
                _print(f"  {saved} frames  ({time.monotonic() - started:.0f}s elapsed)")

    elapsed = time.monotonic() - started
    total_bytes = sum(p.stat().st_size for p in frames_dir.iterdir() if p.is_file())
    summary = {
        "session_id": session_id,
        "label": args.label,
        "window_title": title,
        "region": region,
        "requested_seconds": args.seconds,
        "elapsed_seconds": round(elapsed, 2),
        "requested_fps": args.fps,
        "saved_frames": saved,
        "scale": args.scale,
        "format": "jpeg" if args.jpeg else "png",
        "megabytes": round(total_bytes / 1_048_576, 1),
        "source_mode": "live_capture_readonly",
        "note": "Read-only screen capture. No input was sent to the application.",
    }
    (out_dir / "session.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    _print(f"\ndone: {saved} frames, {summary['megabytes']} MB in {elapsed:.0f}s")
    _print(f"manifest: {manifest.relative_to(ROOT)}")
    return 0


def source_start(started_monotonic: float) -> float:
    """Wall-clock time corresponding to the monotonic start, for stable elapsed values."""
    return time.time() - (time.monotonic() - started_monotonic)


if __name__ == "__main__":
    raise SystemExit(main())
