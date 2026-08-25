from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from huntlab.status import read_status

STATUS_PATH = Path(os.environ.get("HUNTLAB_STATUS_PATH", "runs/latest_status.json"))
app = FastAPI(title="HuntLab Read-Only Overlay", version="0.1.0")


@app.get("/status")
def status() -> dict[str, object]:
    return read_status(STATUS_PATH)


@app.get("/", response_class=HTMLResponse)
def overlay() -> str:
    return """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>HuntLab</title>
  <style>
    body { font-family: system-ui, sans-serif; background: transparent; color: white; margin: 0; }
    .card { background: rgba(0,0,0,.72); border-radius: 14px; padding: 18px; width: 420px; }
    .source { font-size: 12px; text-transform: uppercase; letter-spacing: .12em; opacity: .75; }
    .phase { font-size: 28px; font-weight: 700; margin: 6px 0 12px; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .metric { background: rgba(255,255,255,.08); padding: 10px; border-radius: 9px; }
    .label { font-size: 11px; opacity: .7; }
    .value { font-size: 20px; }
  </style>
</head>
<body>
  <div class="card">
    <div id="source" class="source">SOURCE: NONE</div>
    <div id="phase" class="phase">unknown</div>
    <div class="grid">
      <div class="metric"><div class="label">Proposal</div><div id="proposal" class="value">none</div></div>
      <div class="metric"><div class="label">Confidence</div><div id="confidence" class="value">0%</div></div>
      <div class="metric"><div class="label">Encounters</div><div id="encounters" class="value">0</div></div>
      <div class="metric"><div class="label">Targets</div><div id="targets" class="value">0</div></div>
    </div>
  </div>
<script>
async function refresh() {
  const r = await fetch('/status', {cache: 'no-store'});
  const s = await r.json();
  document.getElementById('source').textContent = 'SOURCE: ' + String(s.source || 'none').toUpperCase();
  document.getElementById('phase').textContent = s.phase || 'unknown';
  document.getElementById('proposal').textContent = s.proposal || 'none';
  document.getElementById('confidence').textContent = Math.round((s.confidence || 0) * 100) + '%';
  document.getElementById('encounters').textContent = s.encounters || 0;
  document.getElementById('targets').textContent = s.target_encounters || 0;
}
setInterval(refresh, 1000); refresh();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "huntlab.overlay.app:app",
        host=os.environ.get("HUNTLAB_OVERLAY_HOST", "127.0.0.1"),
        port=int(os.environ.get("HUNTLAB_OVERLAY_PORT", "8765")),
        reload=False,
    )
