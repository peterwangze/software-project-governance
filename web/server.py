#!/usr/bin/env python3
"""SPG local Web console API server.

Reads the real `.governance/` files and exposes a JSON API at
`GET /api/governance` for the local companion dashboard. Also serves the
built `web/dist/` static assets for production single-port use.

This is a stdlib-only HTTP server (no new npm/pip dependencies). It reuses the
shared Markdown readers and CLI context discovery so the dashboard shows real data
instead of hardcoded mock values.

Run standalone:
    python web/server.py                 # API + static dist on :5174
    python web/server.py --port 5180

In dev, `vite.config.js` proxies `/api` here (Vite runs on 5173).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
INFRA = PLUGIN_ROOT / "skills" / "software-project-governance" / "infra"

sys.path.insert(0, str(INFRA))
import governance_readers as readers
from bootstrap_aggregate import parse_risk_summary

# ---------------------------------------------------------------------------
# Local helpers (not in verify_workflow)
# ---------------------------------------------------------------------------

def _evidence_summary(text, limit=8):
    """Count all appended records and return the last records, newest first."""
    count = 0
    rows = deque(maxlen=limit)
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = readers.governance_table_cells(stripped)
        if not cells or not readers.is_evidence_id(cells[0]):
            continue
        count += 1
        if len(cells) < 4:
            continue
        # Columns: EVD-ID | task | category | item | detail... | ref | owner | date | gate | status
        # Defensive slicing — some rows are very wide with embedded pipes in detail.
        evd_id = cells[0]
        task = cells[1] if len(cells) > 1 else ""
        category = cells[2] if len(cells) > 2 else ""
        # status is the last cell that looks like a status; date is near the end.
        status = cells[-1] if cells else ""
        date = cells[-3] if len(cells) >= 3 else ""
        item_label = category or task or evd_id
        rows.append({
            "id": evd_id,
            "task": task,
            "category": category,
            "item": item_label[:80],
            "status": status,
            "date": date,
        })
    return count, list(reversed(rows))


def _release_version_from_manifest():
    """Best-effort release version from the canonical manifest (not plan-tracker)."""
    manifest = PLUGIN_ROOT / "skills" / "software-project-governance" / "core" / "manifest.json"
    if not manifest.is_file():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        return data.get("version")
    except Exception:
        return None


def build_governance_payload(root):
    """Assemble the real governance facts for the dashboard."""
    payload = {
        "project_root": str(root),
        "project_name": root.name,
        "loops": readers.loop_state(root),
    }
    try:
        plan_path = root / ".governance" / "plan-tracker.md"
        plan = plan_path.read_text(encoding="utf-8") if plan_path.is_file() else ""
        config = readers.project_config(plan)
        payload["project_name"] = readers.project_name(plan, config, root)
        # Workflow version lives in plan-tracker ## 项目配置 (governance runtime state).
        payload["workflow_version"] = config.get("工作流版本", "unknown")
        payload["trigger_mode"] = config.get("触发模式", "unknown")
        payload["permission_mode"] = config.get("操作权限模式", "unknown")
        payload["profile"] = config.get("Profile", "unknown")
        # Release version lives in the canonical manifest (shipped code version).
        payload["release_version"] = _release_version_from_manifest()

        ev_path = root / ".governance" / "evidence-log.md"
        if ev_path.is_file():
            ev_text = ev_path.read_text(encoding="utf-8")
            payload["evidence_count"], payload["recent_evidence"] = _evidence_summary(ev_text)
        else:
            payload["evidence_count"] = 0
            payload["recent_evidence"] = []

        risk_path = root / ".governance" / "risk-log.md"
        risk_text = risk_path.read_text(encoding="utf-8") if risk_path.is_file() else ""
        payload["open_risks"] = parse_risk_summary(risk_text, include_rows=True)["rows"]
    except FileNotFoundError as exc:
        payload["error"] = f"governance file missing: {exc.filename or exc}"
    except Exception as exc:  # pragma: no cover - defensive
        payload["error"] = f"{type(exc).__name__}: {exc}"
    return payload


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------

DIST_DIR = PLUGIN_ROOT / "web" / "dist"


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path, content_type):
        if not path.is_file():
            self.send_error(404, "Not found")
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/governance":
            self._send_json(build_governance_payload(self.server.project_root))
            return
        if path == "/api/health":
            self._send_json({"status": "ok", "project_root": str(self.server.project_root)})
            return
        # Static fallback (production single-port serve of web/dist).
        if DIST_DIR.is_dir():
            if path == "/" or path == "":
                self._send_file(DIST_DIR / "index.html", "text/html; charset=utf-8")
                return
            rel = path.lstrip("/")
            candidate = (DIST_DIR / rel).resolve()
            try:
                candidate.relative_to(DIST_DIR.resolve())
            except ValueError:
                self.send_error(403, "Forbidden")
                return
            ctype = "application/octet-stream"
            if rel.endswith(".html"):
                ctype = "text/html; charset=utf-8"
            elif rel.endswith(".js"):
                ctype = "application/javascript; charset=utf-8"
            elif rel.endswith(".css"):
                ctype = "text/css; charset=utf-8"
            elif rel.endswith(".svg"):
                ctype = "image/svg+xml"
            self._send_file(candidate, ctype)
            return
        self.send_error(404, "Not found (no dist build; run in dev with Vite)")

    def do_OPTIONS(self):  # CORS preflight
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, fmt, *args):  # quieter logging
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def main(argv=None):
    p = argparse.ArgumentParser(description="SPG local Web console API server.")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=5174)
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    args = p.parse_args(argv)

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.project_root = args.project_root.resolve()
    print(f"SPG API server: http://{args.host}:{args.port}/api/governance")
    print(f"Project root: {server.project_root}")
    print(f"Static dist: {'available' if DIST_DIR.is_dir() else 'not built (dev mode via Vite)'}")
    print("Boundary: read-only local companion dashboard; does not execute agent tasks.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSPG API server stopped.")
        server.shutdown()


if __name__ == "__main__":
    main()
