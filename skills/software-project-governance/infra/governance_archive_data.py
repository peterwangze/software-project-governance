"""Read hot and archived governance rows and reconcile the archive index."""

import importlib.util
from pathlib import Path
import re


class GovernanceDataSource:
    """Unified governance data source — transparently aggregates hot files
    + archive files. Backward compatible: falls back to single-file mode
    when archive/ directory does not exist."""

    def __init__(self, governance_dir, sample_path=None, evidence_path=None, archive_index_path=None,
                 archive_root=None, decision_path=None, risk_path=None):
        self.__default_governance_dir = Path(governance_dir)
        self.sample_path = Path(sample_path) if sample_path is not None else self.__default_governance_dir / "plan-tracker.md"
        self.evidence_path = Path(evidence_path) if evidence_path is not None else self.__default_governance_dir / "evidence-log.md"
        self.decision_path = Path(decision_path) if decision_path is not None else self.__default_governance_dir / "decision-log.md"
        self.risk_path = Path(risk_path) if risk_path is not None else self.__default_governance_dir / "risk-log.md"

        if archive_root is not None:
            self.archive_root = Path(archive_root)
        elif archive_index_path is not None:
            self.archive_root = Path(archive_index_path).parent
        else:
            self.archive_root = self._infer_governance_dir() / "archive"

        self.archive_index_path = (
            Path(archive_index_path)
            if archive_index_path is not None
            else self.archive_root / "index.md"
        )
        self.archive_tasks_dir = self.archive_root / "tasks"
        self.archive_evidence_dir = self.archive_root / "evidence"
        self.archive_decisions_dir = self.archive_root / "decisions"
        self.archive_risks_dir = self.archive_root / "risks"

    @staticmethod
    def _table_cells(line):
        from governance_readers import markdown_table_cells
        return markdown_table_cells(line)

    @staticmethod
    def _expand_task_ids(text):
        return expand_task_ids(text)

    def _infer_governance_dir(self):
        for path in (self.sample_path, self.evidence_path):
            if path.name in {"plan-tracker.md", "evidence-log.md"}:
                return path.parent
        return self.__default_governance_dir

    def _has_archive(self):
        """Check if archive directory exists and has content."""
        return self.archive_index_path.exists()

    def _scan_archive_files(self, dir_path, extract_func):
        """Scan all .md files in archive directory (excluding .gitkeep),
        applying extract_func to each, returning aggregated results."""
        results = []
        if not self._has_archive():
            return results
        if not dir_path.exists():
            return results
        for f in sorted(dir_path.glob("*.md")):
            if f.name == ".gitkeep":
                continue
            results.extend(extract_func(f))
        return results

    # ── Task data ──

    def get_all_completed_task_ids(self):
        """Return set of completed task IDs from plan-tracker + archive/tasks/*."""
        return {
            entry["id"]
            for entry in self.get_all_completed_task_entries()
        }

    def get_all_completed_task_entries(self):
        """Return completed task entries with source metadata.

        FIX-480: the hot face reads through the SINGLE parse source —
        ``task_priority.parse_task_dependencies`` — so the 0.99 compact
        shape and the 0.54-era id-first 20-column host shape converge on
        one TaskDep model (no second semantic source; the pre-fix
        profile-column channel mis-located the status cell on the 20-col
        shape and reported ``Completed tasks: 0`` — the python_game false
        PASS). Completion keeps BOTH historical wordings: the ✅ semantics
        (``TaskDep.is_completed``) and the exact ``已完成`` cell (the
        lightweight/profile-column channel's word, kept so trackers using
        the bare word stay counted).
        """
        completed = []
        if self.sample_path.is_file():
            content = self.sample_path.read_text(encoding="utf-8")
            try:
                from task_priority import parse_task_dependencies  # noqa: WPS433 (deferred, matches the module's TPA call style)
                tasks = parse_task_dependencies(content)
            except Exception:  # unreadable/unparsable → empty, never crash
                tasks = []
            for dep in tasks:
                if dep.is_completed() or dep.status.strip() == "已完成":
                    completed.append(
                        {"id": dep.task_id, "status": dep.status,
                         "source": "hot"})
        for entry in self._scan_archive_files(self.archive_tasks_dir, self._extract_task_ids):
            if entry.get("status") == "已完成":
                completed.append({**entry, "source": "archive"})
        return completed

    def _extract_task_ids(self, file_path):
        """Extract task IDs and statuses from an archive task file."""
        results = []
        content = file_path.read_text(encoding="utf-8")
        current_version = None
        for line in content.split("\n"):
            stripped = line.strip()
            # Detect version headers
            m_ver = re.match(r"^#{1,6}\s+(?:v)?(\d+\.\d+\.\d+)\s*[—\-]", stripped)
            if m_ver:
                current_version = m_ver.group(1)
                continue
            # Parse task rows
            m = re.match(r"\|\s*([A-Z]+-\d+)\s*\|", stripped)
            if m:
                task_id = m.group(1)
                parts = self._table_cells(line)
                status = parts[9] if len(parts) >= 10 else "?"
                results.append({"id": task_id, "status": status, "version": current_version})
        return results

    def get_all_task_ids(self):
        """Return set of all task IDs (any status) from hot + archive."""
        task_ids = set()
        # Hot file
        if self.sample_path.is_file():
            content = self.sample_path.read_text(encoding="utf-8")
            for line in content.split("\n"):
                stripped = line.strip()
                if not stripped.startswith("| "):
                    continue
                m = re.match(r"\|\s*([A-Z]+-\d+)\s*\|", stripped)
                if m:
                    task_ids.add(m.group(1))
        # Archive files
        for entry in self._scan_archive_files(self.archive_tasks_dir, self._extract_task_ids):
            task_ids.add(entry["id"])
        return task_ids

    # ── Evidence data ──

    def get_all_evidence_task_ids(self):
        """Return set of task IDs that have evidence entries (hot + archive)."""
        task_ids = set()
        # Hot file
        if self.evidence_path.is_file():
            content = self.evidence_path.read_text(encoding="utf-8")
            for line in content.split("\n"):
                stripped = line.strip()
                if not stripped.startswith("| EVD-"):
                    continue
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 3:
                    raw_ids = parts[2]
                    if raw_ids and re.search(r"[A-Z]+-\d+", raw_ids):
                        task_ids |= self._expand_task_ids(raw_ids)
        # Archive files
        for entry in self._scan_archive_files(self.archive_evidence_dir, self._extract_evidence_entries):
            raw_ids = entry.get("task_ids", "")
            if raw_ids and re.search(r"[A-Z]+-\d+", raw_ids):
                task_ids |= self._expand_task_ids(raw_ids)
        return task_ids

    def get_all_evidence_task_map(self):
        """Return task_id -> evidence IDs from hot evidence-log + archive evidence files."""
        task_map = {}

        def add_entry(evd_id, raw_ids):
            if raw_ids and re.search(r"[A-Z]+-\d+", raw_ids):
                for task_id in self._expand_task_ids(raw_ids):
                    task_map.setdefault(task_id, []).append(evd_id)

        if self.evidence_path.is_file():
            content = self.evidence_path.read_text(encoding="utf-8")
            for line in content.split("\n"):
                line = line.strip()
                if not line.startswith("| EVD-"):
                    continue
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 3:
                    add_entry(parts[1], parts[2])

        for entry in self._scan_archive_files(self.archive_evidence_dir, self._extract_evidence_entries):
            add_entry(entry.get("evd_id", ""), entry.get("task_ids", ""))

        return task_map

    def _extract_evidence_entries(self, file_path):
        """Extract evidence entries from an archive evidence file."""
        results = []
        content = file_path.read_text(encoding="utf-8")
        for line in content.split("\n"):
            stripped = line.strip()
            if not stripped.startswith("| EVD-"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3:
                results.append({
                    "evd_id": parts[1],
                    "task_ids": parts[2],
                })
        return results

    # ── Row-family layer surface (FEAT-076: the unified read entry) ──
    #
    # The evidence-log's four row families (EVD/REVIEW/TRIAGE/RECO) now live
    # across TWO layers: the hot working set (evidence-log.md) and the cold
    # archive (archive/evidence/*.md). This surface is the single read entry
    # layering-aware consumers use (DEC-282 C-1(b) condition 3: 统一入口或
    # 过渡适配) — direct hot-file reads stay valid ONLY for write targets
    # and current-ticket semantics (this-session rows are always hot).

    #: Row-id line prefixes per family (mirror of archive._ROW_FAMILY_LINE_
    #: PREFIXES — kept literal to avoid an import cycle; the archive module
    #: is the write-side authority, this is the read-side mirror).
    FAMILY_ROW_PREFIXES = {
        "EVD": "| EVD-",
        "REVIEW": "| REVIEW-",
        "TRIAGE": "| TRIAGE-",
        "RECO": "| RECO-",
    }

    def _hot_family_lines(self, family):
        """Family-prefixed table rows from the hot evidence-log."""
        prefix = self.FAMILY_ROW_PREFIXES[family]
        if not self.evidence_path.is_file():
            return []
        return [
            line for line in self.evidence_path.read_text(
                encoding="utf-8").split("\n")
            if line.strip().startswith(prefix)
        ]

    def _cold_family_lines(self, family):
        """Family-prefixed table rows from ALL archive evidence files
        (sorted by filename → deterministic order)."""
        prefix = self.FAMILY_ROW_PREFIXES[family]
        rows = []
        for f in self._cold_evidence_files():
            for line in f.read_text(encoding="utf-8").split("\n"):
                if line.strip().startswith(prefix):
                    rows.append({"line": line, "file": f"archive/evidence/{f.name}"})
        return rows

    def _cold_evidence_files(self):
        from archive_indexing import evidence_archive_files
        yield from evidence_archive_files(self.archive_evidence_dir)

    def get_all_family_rows(self, family):
        """FEAT-076: ALL rows of one family across BOTH layers.

        Returns a list of {"row_id", "task_ids", "line", "source", "file"}
        dicts — hot rows carry source="hot" / file=".governance/
        evidence-log.md", cold rows carry source="cold" / their archive
        file. Row id + task ids come from the first two cells (same
        convention every family parser uses).
        """
        if family not in self.FAMILY_ROW_PREFIXES:
            raise ValueError(f"unknown row family {family!r}")
        from archive_indexing import iter_evidence_family_rows
        return list(iter_evidence_family_rows(
            self.evidence_path, self._cold_evidence_files(), self.FAMILY_ROW_PREFIXES[family]))

    def get_all_family_row_ids(self, family):
        """FEAT-076: set of row ids for one family across both layers."""
        return {r["row_id"] for r in self.get_all_family_rows(family)}

    def find_row(self, row_id):
        """FEAT-076: locate ONE row by id across both layers (hot first —
        the working set wins any id collision by design: new rows are
        always written hot). Returns the get_all_family_rows record or
        None."""
        prefix = row_id.split("-", 1)[0] + "-"
        for family, fam_prefix in self.FAMILY_ROW_PREFIXES.items():
            if fam_prefix.lstrip("| ").startswith(prefix):
                for r in self.get_all_family_rows(family):
                    if r["row_id"] == row_id:
                        return r
        return None

    def layer_stats(self):
        """FEAT-076: per-family hot/cold row counts + the three-track size
        basis (DEC-278 Q5: 热工作集容量 / 全库完整性 / 总量增长监测).

        Hot bytes = the hot file's on-disk size (Check 28s basis). Cold
        bytes = the summed sizes of every archive evidence file. Total =
        hot + cold (the full-library volume the growth track monitors).
        """
        stats = {"families": {}, "layers": {}}
        for family in self.FAMILY_ROW_PREFIXES:
            hot_rows = self._hot_family_lines(family)
            cold = self._cold_family_lines(family)
            stats["families"][family] = {
                "hot_rows": len(hot_rows),
                "cold_rows": len(cold),
                "total_rows": len(hot_rows) + len(cold),
            }
        hot_bytes = (self.evidence_path.stat().st_size
                     if self.evidence_path.is_file() else 0)
        cold_bytes = sum(f.stat().st_size for f in self._cold_evidence_files())
        stats["layers"] = {
            "hot_bytes": hot_bytes,
            "cold_bytes": cold_bytes,
            "total_bytes": hot_bytes + cold_bytes,
        }
        return stats

    # ── Decision data ──

    def get_all_decision_ids(self):
        """Return sorted set of decision integers from hot + archive."""
        ids = set()
        # Hot file
        if self.decision_path.is_file():
            content = self.decision_path.read_text(encoding="utf-8")
            for m in re.finditer(r"\bDEC-(\d+)\b", content):
                ids.add(int(m.group(1)))
        # Archive files
        for f in sorted((self.archive_decisions_dir).glob("*.md")):
            if f.name == ".gitkeep":
                continue
            content = f.read_text(encoding="utf-8")
            for m in re.finditer(r"\bDEC-(\d+)\b", content):
                ids.add(int(m.group(1)))
        return sorted(ids)

    # ── Risk data ──

    def get_all_risk_ids(self):
        """Return sorted set of risk integers from hot + archive."""
        ids = set()
        # Hot file
        if self.risk_path.is_file():
            content = self.risk_path.read_text(encoding="utf-8")
            for m in re.finditer(r"\bRISK-(\d+)\b", content):
                ids.add(int(m.group(1)))
        # Archive files
        for f in sorted((self.archive_risks_dir).glob("*.md")):
            if f.name == ".gitkeep":
                continue
            content = f.read_text(encoding="utf-8")
            for m in re.finditer(r"\bRISK-(\d+)\b", content):
                ids.add(int(m.group(1)))
        return sorted(ids)

    # ── Lookup ──

    def find_entry_by_id(self, entry_id):
        """Find an entry by ID: check hot files first, then archive index,
        then archive files. Returns dict with 'source' and 'content' keys,
        or None if not found.

        Supports: EVD-, DEC-, RISK-, and generic Task ID (e.g. FIX-001)
        prefixes.  Uses \b word-boundary matching to avoid false matches
        (EVD-10 will not match EVD-100).
        """
        boundary_pattern = re.compile(
            rf"\b{re.escape(entry_id)}\b"
        )

        # ── Task ID (e.g. FIX-001, AUDIT-082) ──
        if re.match(r"[A-Z]+-\d+", entry_id) and not entry_id.startswith(
            ("EVD-", "DEC-", "RISK-")
        ):
            # 1) plan-tracker (hot)
            if self.sample_path.is_file():
                for line in self.sample_path.read_text(encoding="utf-8").split("\n"):
                    if boundary_pattern.search(line):
                        return {
                            "source": "plan-tracker.md (hot)",
                            "line": line.strip(),
                        }
            # 2) archive index
            if self.archive_index_path.is_file():
                for line in self.archive_index_path.read_text(encoding="utf-8").split("\n"):
                    if boundary_pattern.search(line):
                        return {
                            "source": "archive/index.md",
                            "line": line.strip(),
                        }
            # 3) archive task files
            for f in sorted((self.archive_tasks_dir).glob("*.md")):
                if f.name == ".gitkeep":
                    continue
                for line in f.read_text(encoding="utf-8").split("\n"):
                    if boundary_pattern.search(line):
                        return {
                            "source": f"archive/tasks/{f.name}",
                            "line": line.strip(),
                        }
            return None

        # ── Evidence IDs ──
        if re.match(r"EVD-\d+", entry_id):
            content = self.evidence_path.read_text(encoding="utf-8") if self.evidence_path.is_file() else ""
            for line in content.split("\n"):
                if boundary_pattern.search(line):
                    return {"source": "evidence-log.md (hot)", "line": line.strip()}
            # Search archive
            for f in sorted((self.archive_evidence_dir).glob("*.md")):
                if f.name == ".gitkeep":
                    continue
                fc = f.read_text(encoding="utf-8")
                for line in fc.split("\n"):
                    if boundary_pattern.search(line):
                        return {"source": f"archive/evidence/{f.name}", "line": line.strip()}

        # ── Decision IDs ──
        if re.match(r"DEC-\d+", entry_id):
            if self.decision_path.is_file():
                for line in self.decision_path.read_text(encoding="utf-8").split("\n"):
                    if boundary_pattern.search(line):
                        return {"source": "decision-log.md (hot)", "line": line.strip()}
            # Search archive decisions
            for f in sorted((self.archive_decisions_dir).glob("*.md")):
                if f.name == ".gitkeep":
                    continue
                for line in f.read_text(encoding="utf-8").split("\n"):
                    if boundary_pattern.search(line):
                        return {"source": f"archive/decisions/{f.name}", "line": line.strip()}

        # ── Risk IDs ──
        if re.match(r"RISK-\d+", entry_id):
            if self.risk_path.is_file():
                for line in self.risk_path.read_text(encoding="utf-8").split("\n"):
                    if boundary_pattern.search(line):
                        return {"source": "risk-log.md (hot)", "line": line.strip()}
            # Search archive risks
            for f in sorted((self.archive_risks_dir).glob("*.md")):
                if f.name == ".gitkeep":
                    continue
                for line in f.read_text(encoding="utf-8").split("\n"):
                    if boundary_pattern.search(line):
                        return {"source": f"archive/risks/{f.name}", "line": line.strip()}

        return None


def _load_archive_module(*, plugin_root, host_root):
    archive_path = plugin_root / "skills/software-project-governance/infra/archive.py"
    if not archive_path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("governance_archive_runtime", archive_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # archive.py reads governance FACTS (.governance/...) — point it at the
    # host project, not the plugin cache (FIX-187 / DEC-080 dual-root).
    # host_root is rebound together with plugin_root (FIX-242 P3-3): the
    # attribute defaults to archive.py's own cwd-derived resolve, which can
    # drift from the host root resolved/validated here (e.g. after an
    # explicit --project-root override). archive.py's own --project-root
    # path is unaffected — it is only applied inside archive.main(), which
    # this loader never invokes.
    module.ROOT = host_root
    module.HOST_PROJECT_ROOT = host_root
    return module


def parse_completed_task_ids(*, plan_path):
    """Return set of completed task IDs from plan-tracker."""
    content = plan_path.read_text(encoding="utf-8")
    completed = set()
    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("| ") or "---" in line:
            continue
        m = re.search(r"\|\s*(?:\*\*)?([A-Z]+-\d+)(?:\*\*)?\s*\|", line)
        if not m:
            continue
        task_id = m.group(1)
        parts = [p.strip() for p in line.split("|")]
        if any("已完成" in part for part in parts):
            completed.add(task_id)
    return completed


def check_archive_integrity(*, plan_path, governance_dir, plan_directory, load_archive):
    """Check 27: Verify archive integrity.

    Checks:
      1. archive/index.md referenced archive files all exist
      2. Archive file entries have corresponding index entries
      3. Task count conservation: hot + archive tasks == expected

    Returns:
        dict with keys: pass, issues, total_archived_tasks, index_entries,
                        hot_tasks, total_expected
    """
    result = {
        "pass": True,
        "issues": [],
        "total_archived_tasks": 0,
        "index_entries": 0,
        "hot_tasks": 0,
        "total_expected": 0,
        "pending_archive_tasks": 0,
        "archive_triggers": [],
    }

    archive_index = plan_directory() / "archive" / "index.md"
    archive_tasks_dir = plan_directory() / "archive" / "tasks"
    archive_evidence_dir = plan_directory() / "archive" / "evidence"

    archive_module = load_archive()
    if archive_module is not None:
        analysis = archive_module.analyze_auto_archive_candidates()
        # FIX-416: the actionable face must count EVERY migratable family.
        # The old tasks-only interpolation printed "0 hot completed
        # task(s)" while the gap actually lived in the non-EVD row
        # families (REVIEW/TRIAGE/RECO) — a misleading red whose hinted
        # command (then an EVD-leg CLI default) could not even drain it.
        families = analysis.get("row_families_archived", {}) or {}
        actionable_total = (
            analysis.get("tasks_archived", 0)
            + analysis.get("evidence_archived", 0)
            + analysis.get("decisions_archived", 0)
            + analysis.get("risks_archived", 0)
            # non-EVD families only — EVD is already counted in
            # evidence_archived (no double counting).
            + sum(v for k, v in families.items() if k != "EVD")
        )
        result["pending_archive_tasks"] = actionable_total
        result["archive_triggers"] = analysis.get("triggers", [])
        if analysis.get("should_archive"):
            family_face = ", ".join(
                f"{k}={v}" for k, v in sorted(families.items()) if v
            )
            breakdown = (
                f"tasks={analysis.get('tasks_archived', 0)}, "
                f"evidence={analysis.get('evidence_archived', 0)}, "
                f"decisions={analysis.get('decisions_archived', 0)}, "
                f"risks={analysis.get('risks_archived', 0)}"
            )
            if family_face:
                breakdown += f", families={family_face}"
            result["pass"] = False
            result["issues"].append(
                "Archive trigger gap: "
                f"{actionable_total} archivable row(s) ({breakdown}) "
                f"should be archived via {', '.join(analysis.get('triggers', []))} "
                f"for v{analysis.get('versions_range', ('?', '?'))[0]}~"
                f"v{analysis.get('versions_range', ('?', '?'))[1]}. "
                "Run archive.py migrate --auto."
            )

    # If no archive index, integrity can still pass when no trigger gap exists.
    if not archive_index.exists():
        # But check if there are orphan archive files
        has_archive_files = False
        for d in [archive_tasks_dir, archive_evidence_dir]:
            if d.exists():
                for f in d.glob("*.md"):
                    if f.name != ".gitkeep":
                        has_archive_files = True
                        break
            if has_archive_files:
                break
        if has_archive_files:
            result["pass"] = False
            result["issues"].append(
                "Archive files exist but index.md is missing. Run archive.build_index() to rebuild."
            )
        # Count hot tasks for the check output even before first archive.
        if plan_path.is_file():
            content = plan_path.read_text(encoding="utf-8")
            for line in content.split("\n"):
                stripped = line.strip()
                if not stripped.startswith("| ") or "---" in stripped:
                    continue
                if re.match(r"\|\s*([A-Z]+-\d+)\s*\|", stripped):
                    result["hot_tasks"] += 1
        result["total_expected"] = result["hot_tasks"]
        return result

    # ── FIX-184 (DEC-090/091 P2-1): delegate Check 1 + Check 2 ──
    # The index↔archive-file consistency checks are now delegated to
    # archive.py verify_archive_integrity(), whose _parse_index_section()
    # correctly resets `in_section` on a new `## ` header and parses each
    # section by exact name (including `## 非结构化归档`, which the legacy
    # parser here matched only by accident). When the archive module is
    # unavailable, fall back to the preserved inline parser
    # _legacy_parse_index_refs() to avoid behavior loss.
    index_content = archive_index.read_text(encoding="utf-8")
    index_lines = index_content.split("\n")

    archived_integrity = None
    if archive_module is not None:
        try:
            archived_integrity = archive_module.verify_archive_integrity()
        except Exception as exc:
            result["issues"].append(
                f"archive.verify_archive_integrity() raised; using legacy "
                f"index parser fallback. Error: {exc}"
            )
            archived_integrity = None

    if archived_integrity is not None:
        # Check 1 + Check 2 (index↔file consistency) come from the archive
        # module. Merge pass/issues into Check 27's result.
        if not archived_integrity.get("pass", True):
            result["pass"] = False
            for issue in archived_integrity.get("issues", []):
                if issue not in result["issues"]:
                    result["issues"].append(issue)
        # total_index_entries is the authoritative index-row count across
        # all indexed sections (Task/Evidence/Decision/Risk 索引). Use it
        # for Check 27's index_entries field.
        result["index_entries"] = archived_integrity.get("total_index_entries", 0)
    else:
        # Legacy fallback: original inline parser (kept verbatim so behavior
        # is preserved if archive.py fails to load). Known limitation — does
        # not reset `in_section` and matches any `## ` header containing
        # "索引"; `## 非结构化归档` is only matched incidentally.
        indexed_files = _legacy_parse_index_refs(index_lines)

        # Check 1: All indexed files exist
        for ref in sorted(indexed_files):
            filepath = governance_dir / ref
            if not filepath.exists():
                result["pass"] = False
                result["issues"].append(f"Index references non-existent file: {ref}")

        # Check 2: All archive files are in the index
        actual_archive_files = set()
        gov_dir = plan_directory()
        for d in [archive_tasks_dir, archive_evidence_dir]:
            if d.exists():
                for f in d.glob("*.md"):
                    if f.name == ".gitkeep":
                        continue
                    rel = str(f.relative_to(gov_dir)).replace("\\", "/")
                    actual_archive_files.add(rel)

        unindexed = actual_archive_files - indexed_files
        if unindexed:
            result["pass"] = False
            for f in sorted(unindexed):
                result["issues"].append(f"Archive file not in index: {f}")

    # Check 3: Task count conservation
    # Count hot file tasks
    hot_tasks = 0
    if plan_path.is_file():
        content = plan_path.read_text(encoding="utf-8")
        for line in content.split("\n"):
            stripped = line.strip()
            if not stripped.startswith("| ") or "---" in stripped:
                continue
            m = re.match(r"\|\s*([A-Z]+-\d+)\s*\|", stripped)
            if m:
                hot_tasks += 1
    result["hot_tasks"] = hot_tasks

    # Count archived tasks
    archived_count = 0
    if archive_tasks_dir.exists():
        for f in archive_tasks_dir.glob("*.md"):
            if f.name == ".gitkeep":
                continue
            content = f.read_text(encoding="utf-8")
            for line in content.split("\n"):
                stripped = line.strip()
                if not stripped.startswith("| "):
                    continue
                m = re.match(r"\|\s*([A-Z]+-\d+)\s*\|", stripped)
                if m:
                    archived_count += 1
    result["total_archived_tasks"] = archived_count

    # Count index entries — only in the legacy fallback path. When the
    # archive module supplied archived_integrity, index_entries was already
    # set from verify_archive_integrity()'s authoritative total_index_entries.
    if archived_integrity is None:
        index_entry_count = 0
        for line in index_lines:
            stripped = line.strip()
            if stripped.startswith("| ") and re.match(r"\|\s*[A-Z]+-\d+", stripped):
                index_entry_count += 1
        result["index_entries"] = index_entry_count

    result["total_expected"] = hot_tasks + archived_count

    return result


def expand_task_ids(raw_text):
    """Expand range notations and comma-separated task IDs into individual IDs.

    Supported formats:
      - Single: AUDIT-021
      - Comma-separated: AUDIT-045, AUDIT-048
      - Range: AUDIT-015~020  (expands to AUDIT-015 through AUDIT-020)
      - Mixed comma + range: RISK-021, RISK-022, MAINT-002
    Returns a set of individual task IDs.
    """
    result = set()
    # Split by comma first
    for chunk in raw_text.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        # Check for range notation: PREFIX-NUM1~NUM2
        range_match = re.match(r"^([A-Z]+-)(\d+)\s*~\s*(\d+)$", chunk)
        if range_match:
            prefix = range_match.group(1)
            start_num = int(range_match.group(2))
            end_num = int(range_match.group(3))
            for num in range(start_num, end_num + 1):
                result.add(f"{prefix}{num:03d}")
        elif re.match(r"[A-Z]+-\d+", chunk):
            result.add(chunk)
    return result


def _legacy_parse_index_refs(index_lines):
    """FIX-184: preserved inline index-file-reference parser.

    Used only as a fallback when archive.verify_archive_integrity() cannot
    be invoked (archive module failed to load). Reproduces the original
    Check 27 parser verbatim, including its known limitations (does not
    reset `in_section` on a new `## ` header; matches any header
    containing "索引"). Prefer archive.verify_archive_integrity() which
    parses each section by exact name and correctly resets state.

    Returns the set of `archive/...` references found in index rows.
    """
    indexed_files = set()
    in_section = False
    table_started = False
    for line in index_lines:
        stripped = line.strip()
        if stripped.startswith("## ") and "索引" in stripped:
            in_section = True
            table_started = False
            continue
        if not in_section:
            continue
        if "|---" in stripped:
            table_started = True
            continue
        if not table_started or not stripped.startswith("| "):
            continue

        parts = [p.strip() for p in line.split("|")]
        for part in parts:
            if part.startswith("archive/"):
                indexed_files.add(part)
    return indexed_files
