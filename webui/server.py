"""FastAPI bridge — serves real project data to the webui operator console.

Implements the shapes declared in webui/frontend/src/api/contract.js on top of
whatever the pipeline has already written to projects/<name>/ (state.json,
results.tsv, eval_logs, briefs, edit_logs, chapters). Read-only phase: run
launching / settings mutation come later with a RunManager.

Run from the repo root:
    uv run uvicorn server:app --app-dir webui --port 8600

The vite dev server proxies /api -> http://127.0.0.1:8600 (vite.config.js).
Single-user local console: project resolution goes through paths.py's global
set_project_name under a lock, not a per-request context.
"""

import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

ROOT = Path(__file__).resolve().parent.parent
for _p in (ROOT, ROOT / "scratch"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from core import paths  # noqa: E402
import gen_webui_fixtures as gen  # noqa: E402
from pipeline import pipeline_infra  # noqa: E402

app = FastAPI(title="autonovel operator console", docs_url="/api/docs")

_proj_lock = threading.Lock()


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def default_project() -> str:
    """Most recently touched project (state.json mtime) — the active one."""
    cands = []
    for d in (paths.get_root_dir() / "projects").iterdir():
        sf = d / "state.json"
        if d.is_dir() and sf.exists():
            cands.append((sf.stat().st_mtime, d.name))
    if not cands:
        raise HTTPException(404, "no projects with state.json under projects/")
    return max(cands)[1]


def project_dir(name: str | None) -> tuple[str, Path]:
    """Validate the project name (path-isolation check) and return (name, dir)."""
    resolved = name or default_project()
    with _proj_lock:
        try:
            paths.set_project_name(resolved)
        except ValueError as e:
            raise HTTPException(400, str(e)) from e
        p = paths.get_project_dir()
    if not (p / "state.json").exists():
        raise HTTPException(404, f"unknown project: {resolved}")
    return resolved, p


def load_state(p: Path) -> dict:
    return json.loads((p / "state.json").read_text(encoding="utf-8"))


def norm_phase(state: dict) -> str:
    if state.get("current_focus") == "done":
        return "idle"
    phase = state.get("phase", "idle") or "idle"
    return "export" if phase.startswith("complete") else phase


@app.get("/api/projects")
def list_projects():
    name, p = project_dir(None)
    return gen.gen_projects(load_state(p), p)


@app.get("/api/run-state")
def run_state(project: str | None = Query(None)):
    name, p = project_dir(project)
    state = load_state(p)
    return {
        "project": name,
        "phase": norm_phase(state),
        "iteration": state.get("iteration", 0),
        "foundationScore": state.get("foundation_score", 0) or 0,
        "loreScore": state.get("lore_score", 0) or 0,
        "stallCount": state.get("foundation_stall_count", 0),
        "startedAt": _iso((p / "state.json").stat().st_mtime),
        "running": False,  # no RunManager yet — true liveness lands with run launch
    }


@app.get("/api/score-history")
def score_history(project: str | None = Query(None)):
    _, p = project_dir(project)
    results = p / "results.tsv"
    out = []
    if results.exists():
        for i, line in enumerate(results.read_text(encoding="utf-8").splitlines()[1:], 1):
            parts = line.split("\t")
            if len(parts) < 6:
                continue
            _commit, phase, score, _words, status, _desc = parts[:6]
            out.append({
                "iteration": i,
                "score": float(score),
                "kept": status == "keep",
                "phase": phase,
            })
    return out


@app.get("/api/llm-events")
def llm_events(project: str | None = Query(None)):
    _, p = project_dir(project)
    events = []
    f = p / "llm_events.jsonl"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            e = json.loads(line)
            events.append({
                "ts": e.get("ts"),
                "modelKey": e.get("model_key"),
                "model": e.get("model"),
                "ok": e.get("ok"),
                "attempt": e.get("attempt"),
                "tokensIn": e.get("tokens_in"),
                "tokensOut": e.get("tokens_out"),
                "durationMs": e.get("duration_ms"),
                "stopReason": e.get("stop_reason"),
                "promptChars": e.get("prompt_chars"),
                "responseChars": e.get("response_chars"),
                "promptHead": e.get("prompt_head"),
            })
    return events


@app.get("/api/foundation")
def foundation(project: str | None = Query(None)):
    _, p = project_dir(project)
    return gen.gen_foundation(p, load_state(p))


@app.get("/api/ledger")
def ledger(project: str | None = Query(None)):
    _, p = project_dir(project)
    return gen.gen_ledger(p, load_state(p))


@app.get("/api/chapters")
def chapters(project: str | None = Query(None)):
    _, p = project_dir(project)
    return gen.gen_chapters(p, load_state(p))


@app.get("/api/evals")
def evals(project: str | None = Query(None)):
    _, p = project_dir(project)
    return gen.gen_evals(p)


@app.get("/api/revision")
def revision(project: str | None = Query(None)):
    _, p = project_dir(project)
    return gen.gen_revision(p)


@app.get("/api/tournament")
def tournament(project: str | None = Query(None)):
    _, p = project_dir(project)
    return gen.gen_tournament(p)


def _mask(key: str | None) -> str:
    if not key:
        return ""
    return f"{key[:7]}…{key[-4:]}" if len(key) > 14 else "…"


@app.get("/api/settings")
def settings():
    # paths.py loads .env at import; pipeline_infra owns the gate constants.
    return {
        "baseUrl": os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
        "apiKeyMasked": _mask(os.getenv("ANTHROPIC_API_KEY")),
        "models": {r: os.getenv(f"AUTONOVEL_{r.upper()}_MODEL", "writer_combo")
                   for r in ("writer", "judge", "review")},
        "thresholds": {
            "foundation": pipeline_infra.FOUNDATION_THRESHOLD,
            "chapter": pipeline_infra.CHAPTER_THRESHOLD,
        },
        "heuristics": {
            "maxChapterAttempts": pipeline_infra.MAX_CHAPTER_ATTEMPTS,
            "revisionCycles": pipeline_infra.MIN_REVISION_CYCLES,
            "plateauDelta": pipeline_infra.PLATEAU_DELTA,
        },
        "defaults": {"genre": "", "chapterCount": 24, "notes": ""},
    }
