"""One-word console launcher.

    uv run gesaku              # static dist (or vite if no dist)
    uv run gesaku --dev        # vite dev + FastAPI bridge
    uv run gesaku --no-open    # don't open a browser

From the repo root. Ctrl+C tears both processes down.
"""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


def _find_root() -> Path:
    env = os.environ.get("GESAKU_ROOT")
    if env:
        root = Path(env).expanduser().resolve()
        if (root / "webui" / "server.py").is_file():
            return root
        raise SystemExit(f"GESAKU_ROOT={root} does not look like a gesaku repo")
    here = Path(__file__).resolve().parent
    if (here / "webui" / "server.py").is_file():
        return here
    cwd = Path.cwd().resolve()
    if (cwd / "webui" / "server.py").is_file():
        return cwd
    raise SystemExit(
        "Run from the gesaku repo root, or set GESAKU_ROOT to that directory."
    )


def _free_port(host: str, port: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        return s.getsockname()[1]


def _wait_for_port(host: str, port: int, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            try:
                s.connect((host, port))
                return True
            except OSError:
                time.sleep(0.15)
    return False


def _npm_cmd() -> list[str]:
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm:
        return []
    return [npm]


def _spawn(args: list[str], cwd: Path | None = None, env: dict | None = None) -> subprocess.Popen:
    return subprocess.Popen(
        args,
        cwd=str(cwd) if cwd else None,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )


def _serve_static(root: Path, host: str, port: int) -> subprocess.Popen:
    """Single process: uvicorn with the SPA mounted at /."""
    code = f"""
import sys
from pathlib import Path
root = Path({str(root)!r})
sys.path[:0] = [str(root), str(root / "webui"), str(root / "scratch")]
from fastapi.staticfiles import StaticFiles
from server import app
dist = root / "webui" / "frontend" / "dist"
app.mount("/", StaticFiles(directory=str(dist), html=True), name="spa")
import uvicorn
uvicorn.run(app, host={host!r}, port={port}, log_level="warning")
"""
    return _spawn([sys.executable, "-c", code], cwd=root)


def _serve_api(root: Path, host: str, api_port: int) -> subprocess.Popen:
    return _spawn(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "server:app",
            "--app-dir",
            str(root / "webui"),
            "--host",
            host,
            "--port",
            str(api_port),
            "--log-level",
            "warning",
        ],
        cwd=root,
    )


def _serve_vite(root: Path, host: str, ui_port: int, api_port: int) -> subprocess.Popen | None:
    npm = _npm_cmd()
    frontend = root / "webui" / "frontend"
    if not npm or not (frontend / "node_modules" / "vite").exists():
        return None
    env = os.environ.copy()
    env["VITE_HOST"] = host
    env["VITE_PORT"] = str(ui_port)
    # vite.config.js proxies /api -> 8600; keep that unless we changed api_port
    return _spawn([*npm, "run", "dev", "--", "--host", host, "--port", str(ui_port), "--strictPort"], cwd=frontend, env=env)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gesaku",
        description="Launch the gesaku operator console (bridge + web UI).",
    )
    parser.add_argument("--dev", action="store_true", help="vite dev server instead of built dist")
    parser.add_argument("--static", action="store_true", help="force serving webui/frontend/dist")
    parser.add_argument("--host", default="127.0.0.1", help="bind address (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8600, help="API/console port (default 8600)")
    parser.add_argument("--ui-port", type=int, default=5175, help="vite port in --dev (default 5175)")
    parser.add_argument("--no-open", action="store_true", help="do not open a browser")
    args = parser.parse_args(argv)

    root = _find_root()
    dist = root / "webui" / "frontend" / "dist" / "index.html"
    use_dev = args.dev or (not args.static and not dist.is_file())
    if args.static:
        use_dev = False
    if not use_dev and not dist.is_file():
        print("No webui/frontend/dist — run `npm run build` in webui/frontend, or pass --dev.", file=sys.stderr)
        return 1

    try:
        api_port = _free_port(args.host, args.port) if args.port else args.port
    except OSError:
        api_port = 0
        # fall back: let uvicorn pick; we re-read from the process later — keep it simple
        api_port = args.port

    procs: list[subprocess.Popen] = []
    try:
        if use_dev:
            ui_port = args.ui_port
            try:
                _free_port(args.host, ui_port)
            except OSError:
                print(f"Port {ui_port} busy — pass --ui-port", file=sys.stderr)
                return 1
            api = _serve_api(root, args.host, api_port)
            procs.append(api)
            if not _wait_for_port(args.host, api_port, timeout=20):
                print(f"API did not come up on {args.host}:{api_port}", file=sys.stderr)
                return 1
            vite = _serve_vite(root, args.host, ui_port, api_port)
            if vite is None:
                print("vite not available (npm or node_modules missing) — try without --dev", file=sys.stderr)
                return 1
            procs.append(vite)
            if not _wait_for_port(args.host, ui_port, timeout=40):
                print(f"vite did not come up on {args.host}:{ui_port}", file=sys.stderr)
                return 1
            url = f"http://{args.host}:{ui_port}"
        else:
            api = _serve_static(root, args.host, api_port)
            procs.append(api)
            if not _wait_for_port(args.host, api_port, timeout=20):
                print(f"Console did not come up on {args.host}:{api_port}", file=sys.stderr)
                return 1
            url = f"http://{args.host}:{api_port}"

        print(f"gesaku console  {url}")
        print(f"  API docs      {url if not use_dev else f'http://{args.host}:{api_port}'}/api/docs")
        print("Ctrl+C to stop.")
        if not args.no_open:
            webbrowser.open(url)

        while True:
            for p in procs:
                rc = p.poll()
                if rc is not None:
                    print(f"process exited (code {rc})", file=sys.stderr)
                    return rc or 1
            time.sleep(0.4)
    except KeyboardInterrupt:
        print("\nshutting down…")
        return 0
    finally:
        for p in procs:
            if p.poll() is None:
                p.terminate()
        for p in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()


if __name__ == "__main__":
    raise SystemExit(main())
