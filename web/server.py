#!/usr/bin/env python3
"""SPG local Web console API server.

Reads the real `.governance/` files and exposes a JSON API at
`GET /api/governance` for the local companion dashboard. Also serves the
built `web/dist/` static assets for production single-port use.

This is a stdlib-only HTTP server (no new npm/pip dependencies). It reuses the
parser functions from `verify_workflow.py` so the dashboard shows real data
instead of hardcoded mock values.

Run standalone:
    python web/server.py                 # API + static dist on :5174
    python web/server.py --port 5180

In dev, `vite.config.js` proxies `/api` here (Vite runs on 5173).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INFRA = ROOT / "skills" / "software-project-governance" / "infra"

# ---------------------------------------------------------------------------
# Reuse the real parsers from verify_workflow (import-first, fallback local).
# ---------------------------------------------------------------------------

try:
    sys.path.insert(0, str(INFRA))
    import verify_workflow as _vw  # type: ignore  # noqa: F401

    def _parse_project_config():
        return _vw.parse_project_config()

    def _parse_gate_status():
        return _vw.parse_gate_status()

    def _parse_overview():
        return _vw.parse_overview()

    def _discover_governance_context(root):
        return _vw.discover_governance_context(root)

    def _count_evidence(text):
        return _vw._count_evidence_rows(text)

    def _table_cells(line):
        return _vw._governance_table_cells(line)

    _IMPORT_OK = True
    _IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - fallback path
    _IMPORT_OK = False
    _IMPORT_ERROR = f"{type(exc).__name__}: {exc}"
    SAMPLE_PATH = ROOT / ".governance" / "plan-tracker.md"

    def _parse_project_config():
        config = {}
        content = SAMPLE_PATH.read_text(encoding="utf-8")
        in_section = False
        for line in content.split("\n"):
            if line.strip() == "## 项目配置":
                in_section = True
                continue
            if in_section and line.startswith("## "):
                break
            if in_section:
                m = re.match(r"- \*\*(.+?)\*\*:\s*(.+)", line)
                if m:
                    config[m.group(1)] = m.group(2)
        return config

    def _parse_gate_status():
        gates = []
        content = SAMPLE_PATH.read_text(encoding="utf-8")
        in_section = False
        for line in content.split("\n"):
            if line.strip() == "## Gate 状态跟踪":
                in_section = True
                continue
            if in_section and line.startswith("## "):
                break
            if in_section and line.startswith("|"):
                parts = [p.strip() for p in line.split("|")[1:-1]]
                if len(parts) >= 5 and parts[0] != "Gate" and not all(
                    set(p.strip()) <= {"-", " "} for p in parts
                ):
                    gates.append({
                        "gate": parts[0],
                        "transition": parts[1],
                        "status": parts[2],
                        "date": parts[3],
                        "evidence": parts[4] if len(parts) > 4 else "",
                    })
        return gates

    def _parse_overview():
        content = SAMPLE_PATH.read_text(encoding="utf-8")
        in_section = False
        for line in content.split("\n"):
            if line.strip() == "## 项目总览":
                in_section = True
                continue
            if in_section and line.startswith("## "):
                break
            if in_section and line.startswith("|"):
                parts = [p.strip() for p in line.split("|")[1:-1]]
                if len(parts) >= 8 and parts[0] != "项目" and not all(
                    set(p.strip()) <= {"-", " "} for p in parts
                ):
                    return {
                        "project": parts[0],
                        "current_stage": parts[1],
                        "total": parts[2],
                        "completed": parts[3],
                        "blocked": parts[4],
                        "risks": parts[5],
                        "latest_gate": parts[6],
                        "latest_retro": parts[7],
                    }
        return {}

    def _discover_governance_context(root):
        return {
            "status": "NOT_FOUND",
            "detected_item": "not found",
            "source_facts": [],
            "blocker_state": "no blocker open risk",
            "next_action": "context discovery unavailable (import fallback)",
            "auto_continue": True,
            "interrupt_boundary": "AskUserQuestion before critical decisions",
        }

    def _count_evidence(text):
        return len(re.findall(r"^(?:EVD-\d+|REVIEW-[A-Z]+-\d+)", text, re.MULTILINE))

    def _table_cells(line):
        cleaned = line.strip()
        for _ in range(2):
            cleaned = cleaned[1:] if cleaned.startswith("|") else cleaned
            cleaned = cleaned[:-1] if cleaned.endswith("|") else cleaned
        return [c.strip() for c in cleaned.split("|")]


# ---------------------------------------------------------------------------
# Local helpers (not in verify_workflow)
# ---------------------------------------------------------------------------

def _parse_recent_evidence(text, limit=8):
    """Top N most recent evidence rows (file is newest-first)."""
    rows = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = _table_cells(stripped)
        if len(cells) < 4:
            continue
        first = cells[0]
        if not re.match(r"^(EVD-\d+|REVIEW-[A-Z]+-\d+)", first):
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
        if len(rows) >= limit:
            break
    return rows


def _parse_open_risks_with_deadline():
    """Open risks with description + deadline from risk-log.md."""
    risk_path = ROOT / ".governance" / "risk-log.md"
    if not risk_path.is_file():
        return []
    risks = []
    for line in risk_path.read_text(encoding="utf-8").split("\n"):
        stripped = line.strip()
        if not stripped.startswith("| RISK-"):
            continue
        cells = _table_cells(stripped)
        if len(cells) < 9:
            continue
        if cells[8] != "打开":
            continue
        desc = cells[2] if len(cells) > 2 else cells[0]
        deadline = cells[10] if len(cells) > 10 else ""
        risks.append({
            "id": cells[0],
            "description": desc[:120],
            "status": cells[8],
            "deadline": deadline,
        })
    return risks


def _release_version_from_manifest():
    """Best-effort release version from the canonical manifest (not plan-tracker)."""
    manifest = ROOT / "skills" / "software-project-governance" / "core" / "manifest.json"
    if not manifest.is_file():
        return None
    try:
        import json as _json
        data = _json.loads(manifest.read_text(encoding="utf-8"))
        return data.get("version")
    except Exception:
        return None


def build_governance_payload():
    """Assemble the real governance facts for the dashboard."""
    payload = {
        "project_root": str(ROOT),
        "project_name": ROOT.name,
        "import_ok": _IMPORT_OK,
    }
    if not _IMPORT_OK:
        payload["import_error"] = _IMPORT_ERROR

    try:
        config = _parse_project_config()
        # Workflow version lives in plan-tracker ## 项目配置 (governance runtime state).
        payload["workflow_version"] = config.get("工作流版本", "unknown")
        payload["trigger_mode"] = config.get("触发模式", "unknown")
        payload["permission_mode"] = config.get("操作权限模式", "unknown")
        payload["profile"] = config.get("Profile", "unknown")
        # Release version lives in the canonical manifest (shipped code version).
        payload["release_version"] = _release_version_from_manifest()

        payload["gates"] = _parse_gate_status()
        payload["overview"] = _parse_overview()
        payload["context"] = _discover_governance_context(str(ROOT))

        ev_path = ROOT / ".governance" / "evidence-log.md"
        if ev_path.is_file():
            ev_text = ev_path.read_text(encoding="utf-8")
            payload["evidence_count"] = _count_evidence(ev_text)
            payload["recent_evidence"] = _parse_recent_evidence(ev_text, 8)
        else:
            payload["evidence_count"] = 0
            payload["recent_evidence"] = []

        payload["open_risks"] = _parse_open_risks_with_deadline()
    except FileNotFoundError as exc:
        payload["error"] = f"governance file missing: {exc.filename or exc}"
    except Exception as exc:  # pragma: no cover - defensive
        payload["error"] = f"{type(exc).__name__}: {exc}"
    return payload


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------

DIST_DIR = ROOT / "web" / "dist"


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
            self._send_json(build_governance_payload())
            return
        if path == "/api/health":
            self._send_json({"status": "ok", "project_root": str(ROOT)})
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
    args = p.parse_args(argv)

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"SPG API server: http://{args.host}:{args.port}/api/governance")
    print(f"Project root: {ROOT}")
    print(f"Static dist: {'available' if DIST_DIR.is_dir() else 'not built (dev mode via Vite)'}")
    print("Boundary: read-only local companion dashboard; does not execute agent tasks.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSPG API server stopped.")
        server.shutdown()


if __name__ == "__main__":
    main()
