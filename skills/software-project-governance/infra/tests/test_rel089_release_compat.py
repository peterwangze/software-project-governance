"""REL-089 — 0.88 M-3 前置补强票：arch 抽检三放行条件的机器看护测试。

条件①（未激活默认的运行时验证 · DEC-240 op-c16d9b24）：
  - 干净安装（零工件）+ 0.87→0.88 升级布局两路径下，发版自举
    （write-guard-bootstrap check-only / converge）不隐式激活：
    ``.write-guard-posture.json`` 不被创建、族姿态全 WARN、
    decision 权威源保持 ``MD_ACTIVE``（epoch 0）；
  - 运行时可查：``load_authority`` + ``--show-posture``
    （``run_guard_management_cli("show_posture", ...)``）在新装/升级
    两路径下如实反映未激活默认。

条件③（持久状态回退兼容证明）：
  - 用 v0.87.0 真实代码（``git show v0.87.0:<path>`` 提取到临时目录，
    子进程隔离运行——FIX-387 的进程内全局态教训）做「0.87 视角」行为测试：
      (a1) 0.87 守卫状态加载器可读 0.88 写入的 ``.write-guard-state.json``
           （schema_version=1 双版一致 + 顶层键集恒等）；
      (b1) 0.87 closure journal 读取器对 0.88 新增事件类型
           （closure_cancelled/closure_reopened/closure_fenced）= 跳过 +
           problems 响亮披露（fail-safe 读），并实证 seq 碰撞向量
           （0.87 resume 会以已占用的 seq 追加——rollback 运行手册门禁依据）；
      (c)  0.87 archive 枚举只扫固定子目录的 *.md——
           ``archive/.migration`` 目录及其内容不被枚举不被触碰；
  - 静态证明：v0.87.0 infra 代码树对 0.88 新工件路径零引用
    （安全忽略的代码 diff 论证机检化）。

定性结论承载：docs/release/rel-089-m3-precondition-report.md（条件②
EVD-1140/EVD-1164 人工复核 + 修复票票面 + rollback-plan 补节文本）。

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_rel089_release_compat.py -v
"""

import argparse
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
_PLUGIN_ROOT = _INFRA_DIR.parent          # skills/software-project-governance
_REPO_ROOT = _PLUGIN_ROOT.parent.parent   # 仓库根（skills 的上一级）
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import verify_workflow as vw  # noqa: E402
import write_guard_state as wgs  # noqa: E402  (FEAT-060/064 state machine)
import decision_repository as drepo  # noqa: E402  (FEAT-061 authority)

_INFRA_PREFIX = "skills/software-project-governance/infra/"

# 0.88-only closure event types（FEAT-062/063；v0.87.0 CLOSURE_EVENT_TYPES
# 封闭枚举不含三者——0.87 读取器必报 unknown event_type problems）。
_EVENT_TYPES_088_ONLY = ("closure_cancelled", "closure_reopened",
                         "closure_fenced")

# 0.88 新持久状态工件（v0.87.0 代码树的未知文件——静态证明对象）。
_ARTIFACTS_UNKNOWN_TO_087 = (
    ".write-guard-violations.json",   # FEAT-060
    ".write-guard-posture.json",      # FEAT-064
    "closure-generations.json",       # FEAT-063
    ".decision-store-state.json",     # FEAT-061
    ".decision-migration",            # FEAT-061/FIX-385 migration root
    ".migration",                     # FEAT-061/FIX-385 big-table（archive/ 下）
)


def _git(*args):
    return subprocess.run(
        ["git", "-C", str(_REPO_ROOT), *args],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=120)


# ═════════════════════════════════════════════════════════════════════════
# 夹具 — 0.87 布局治理目录 + 0.88 状态工件共存世界
# ═════════════════════════════════════════════════════════════════════════

_EVD_SEED = (
    "| EVD-8001 | FEAT-057 | 产品代码 | seed 旧行（amnesty 样本） | "
    "事实依据：存量行 | actor | 2026-09-19 | G11 | ✅ 完成 |\n")
_EVD_SEED2 = (
    "| EVD-8002 | FEAT-057 | 产品代码 | seed 第二行 | "
    "事实依据：存量行 | actor | 2026-09-19 | G11 | ✅ 完成 |\n")
_DEC_SEED = (
    "| DEC-223 | 2026-09-19 | coordinator | seed 决策行 | "
    "依据：存量 |\n")
_REVIEW_SEED = (
    "| REVIEW-FEAT-057-R0 | FEAT-057 | 治理记录 | seed 审查行 | "
    "事实依据：存量 | reviewer | 2026-09-19 | G11 | APPROVED |\n")
_TRACKER_SEED = (
    "| 优先级 | 任务ID | 标题 | 依赖 | 目标版本 | 闭环路径 | 状态 |\n"
    "|---|---|---|---|---|---|---|\n"
    "| **P1** | FEAT-057 | 行族对账夹具票 | — | 0.86.0 | closure | "
    "🔄 进行中 (2026-09-19) |\n")
_OPS_SEED = ('{"operation_id": "op-' + "0" * 32 +
             '", "record_kind": "task_row_update"}\n')


def _seed_gov_rows(gov):
    """0.87 时代布局的治理记录面（受管行族夹具——RowFamilyReconciliationTests
    同构种子）。"""
    gov.mkdir(parents=True, exist_ok=True)
    (gov / "evidence-log.md").write_text(
        _EVD_SEED + _EVD_SEED2 + _REVIEW_SEED, encoding="utf-8")
    (gov / "decision-log.md").write_text(_DEC_SEED, encoding="utf-8")
    (gov / "plan-tracker.md").write_text(_TRACKER_SEED, encoding="utf-8")
    (gov / "plan-tracker.md.ops.jsonl").write_text(_OPS_SEED,
                                                   encoding="utf-8")


def _seed_088_artifacts(gov, *, with_authority_marker=True):
    """0.88 已产生的持久状态工件（四类全量共存——DEC-240③ 清单）。"""
    # (a) guard 台账族
    (gov / ".write-guard-state.json").write_text(
        json.dumps({"schema_version": 1, "tool": "governance-write-guard",
                    "files": {}}, ensure_ascii=False, indent=2,
                   sort_keys=True) + "\n", encoding="utf-8")
    (gov / ".write-guard-violations.json").write_text(
        json.dumps({"schema_version": 1, "tool": wgs.TOOL_ID,
                    "updated_at": None, "violations": {}, "grants": {},
                    "pending_txn": None}, ensure_ascii=False, indent=2,
                   sort_keys=True) + "\n", encoding="utf-8")
    # (b) closure generations sidecar + 0.88 新事件类型 journal
    (gov / "closure-generations.json").write_text(
        json.dumps({"schema_version": 1, "generations": {}},
                   ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    lines = []
    for seq, etype in enumerate(_EVENT_TYPES_088_ONLY, start=1):
        lines.append(json.dumps({
            "event_id": "rel089{0:024d}".format(seq),
            "timestamp": "2026-09-25T00:00:0{0}Z".format(seq),
            "unit_id": "C-REL089", "event_type": etype,
            "cas_version": seq, "from_version": seq - 1,
            "actor": "rel089-fixture", "payload": {},
            "schema_version": 1}, ensure_ascii=False, sort_keys=True))
    (gov / "closure-events.jsonl").write_text(
        "".join(line + "\n" for line in lines), encoding="utf-8")
    # (c) 续迁工件：decision migration root + archive 大表迁移目录
    (gov / ".decision-migration" / "M-REL089-TEST").mkdir(parents=True,
                                                          exist_ok=True)
    (gov / ".decision-migration" / "M-REL089-TEST" / "journal.json") \
        .write_text('{"migration_id": "M-REL089-TEST"}', encoding="utf-8")
    big = (gov / "archive" / ".migration" / "evidence-v0.87.0~v0.88")
    big.mkdir(parents=True, exist_ok=True)
    (big / "journal.json").write_text(
        '{"schema": "archive-big-table-migration/1", "phase": "staged"}',
        encoding="utf-8")
    # (d) decision 权威状态标记（默认 MD_ACTIVE 世界——closed key set
    # 按 _validate_authority_document 契约构造：persisted doc 不含 present）
    if with_authority_marker:
        doc = {k: v for k, v in drepo.initial_authority().items()
               if k != "present"}
        (gov / ".decision-store-state.json").write_text(
            json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n", encoding="utf-8")


def _snapshot(gov):
    out = {}
    for p in sorted(gov.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(gov))] = p.read_bytes()
    return out


# ═════════════════════════════════════════════════════════════════════════
# 条件① — 未激活默认的运行时验证（两路径状态断言）
# ═════════════════════════════════════════════════════════════════════════

class ReleaseBootstrapDefaultPostureTests(unittest.TestCase):
    """干净安装 + 0.87→0.88 升级布局：发版自举不隐式激活，运行时可查。"""

    # ── 干净安装：零工件世界 ─────────────────────────────────────────────

    def test_clean_install_check_only_zero_write_and_defaults(self):
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"          # 不存在 = 干净安装
            with mock.patch.object(vw, "GOVERNANCE_DIR", gov):
                report = vw.check_release_bootstrap_world()
            self.assertTrue(report["converged"], report)
            # check-only 零写入：连治理目录都不应被创建
            self.assertFalse(gov.exists())
            # 权威源可查：缺省 = 初始 md 世界
            auth = drepo.load_authority(gov)
            self.assertEqual(auth["state"], "MD_ACTIVE")
            self.assertEqual(auth["backend"], "md")
            self.assertEqual(auth["epoch"], 0)
            self.assertFalse(auth["present"])
            # 族姿态可查：缺省 = 全 WARN（零足迹）
            postures, issue = wgs.load_family_postures(gov)
            self.assertEqual((postures, issue), ({}, None))

    def test_clean_install_show_posture_reports_all_warn(self):
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = wgs.run_guard_management_cli(
                    "show_posture", argparse.Namespace(),
                    governance_dir=gov)
            self.assertEqual(code, 0)
            out = buf.getvalue()
            self.assertNotIn("BLOCK 已激活", out)
            self.assertEqual(out.count("现值=warn"),
                             len(wgs.FAMILY_VOCABULARY), out)
            self.assertFalse((gov / ".write-guard-posture.json").is_file())

    def test_clean_install_converge_does_not_activate(self):
        """converge（守卫唯一写路径）在零足迹宿主只落守卫自身工件——
        姿态配置与权威标记零创建。"""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"
            with mock.patch.object(vw, "GOVERNANCE_DIR", gov), \
                 mock.patch.object(vw, "SAMPLE_PATH",
                                   gov / "plan-tracker.md"):
                converged, payload = vw.run_release_bootstrap_converge()
            self.assertTrue(converged, payload)
            self.assertFalse((gov / ".write-guard-posture.json").is_file())
            self.assertFalse((gov / ".decision-store-state.json").is_file())
            auth = drepo.load_authority(gov)
            self.assertEqual(auth["state"], "MD_ACTIVE")
            postures, issue = wgs.load_family_postures(gov)
            self.assertEqual((postures, issue), ({}, None))

    # ── 升级路径：0.87 布局 + 0.88 工件共存 ──────────────────────────────

    def _upgrade_world(self, gov):
        _seed_gov_rows(gov)
        _seed_088_artifacts(gov)
        # 用 0.88 真实写入器建立对账基线（= 0.88 已运行过的升级世界）
        with mock.patch.object(vw, "GOVERNANCE_DIR", gov), \
             mock.patch.object(vw, "SAMPLE_PATH", gov / "plan-tracker.md"):
            result = vw.check_governance_write_shapes(persist_state=True)
        failed = sorted(k for k, f in result.items()
                        if isinstance(f, dict) and f.get("status") == "FAIL")
        self.assertEqual(failed, [], result)
        return gov

    def test_upgrade_layout_check_only_zero_write_no_activation(self):
        with tempfile.TemporaryDirectory() as td:
            gov = self._upgrade_world(Path(td) / ".governance")
            before = _snapshot(gov)
            with mock.patch.object(vw, "GOVERNANCE_DIR", gov):
                report = vw.check_release_bootstrap_world()
            self.assertEqual(_snapshot(gov), before)   # check-only 零写入
            self.assertTrue(report["converged"], report)
            self.assertFalse((gov / ".write-guard-posture.json").is_file())
            auth = drepo.load_authority(gov)
            self.assertEqual(auth["state"], "MD_ACTIVE")
            self.assertEqual(auth["backend"], "md")
            self.assertTrue(auth["present"])
            postures, issue = wgs.load_family_postures(gov)
            self.assertEqual((postures, issue), ({}, None))

    def test_upgrade_layout_guard_faces_never_block_class(self):
        """共存世界的 guard 面无 BLOCK 类 issue（姿态全 WARN——即使对账
        产生 WARN 类披露也不升级为 BLOCK）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = self._upgrade_world(Path(td) / ".governance")
            with mock.patch.object(vw, "GOVERNANCE_DIR", gov), \
                 mock.patch.object(vw, "SAMPLE_PATH",
                                   gov / "plan-tracker.md"):
                result = vw.check_governance_write_shapes(
                    persist_state=False)
            for key, face in result.items():
                if not isinstance(face, dict):
                    continue
                self.assertNotEqual(face.get("status"), "FAIL",
                                    (key, face))
                for issue in face.get("issues") or []:
                    self.assertNotEqual(issue.get("posture"), "block",
                                        (key, issue))

    def test_upgrade_layout_converge_writes_only_guard_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"
            _seed_gov_rows(gov)
            _seed_088_artifacts(gov)
            before = _snapshot(gov)
            with mock.patch.object(vw, "GOVERNANCE_DIR", gov), \
                 mock.patch.object(vw, "SAMPLE_PATH",
                                   gov / "plan-tracker.md"):
                converged, payload = vw.run_release_bootstrap_converge()
            self.assertTrue(converged, payload)
            after = _snapshot(gov)
            new_files = set(after) - set(before)
            # converge 只写守卫自身状态工件（FEAT-057/060 契约）
            self.assertTrue(new_files <= {".write-guard-state.json",
                                          ".write-guard-violations.json"},
                            new_files)
            # 不隐式激活：姿态配置文件零创建；权威源仍 MD_ACTIVE
            self.assertNotIn(".write-guard-posture.json", after)
            auth = drepo.load_authority(gov)
            self.assertEqual(auth["state"], "MD_ACTIVE")
            self.assertEqual(auth["epoch"], 0)
            postures, issue = wgs.load_family_postures(gov)
            self.assertEqual((postures, issue), ({}, None))


# ═════════════════════════════════════════════════════════════════════════
# 条件③ — 持久状态回退兼容证明（v0.87.0 视角，子进程隔离）
# ═════════════════════════════════════════════════════════════════════════

class BackwardCompat087ViewTests(unittest.TestCase):
    """提取 v0.87.0 真实代码到临时目录，以 0.87 语义运行读取路径。

    子进程隔离（cwd=提取目录）：0.87 模块与 0.88 同名模块（loop_event_log
    等）互不污染——FIX-387 进程内全局态教训的对面应用。
    """

    @classmethod
    def setUpClass(cls):
        rc = _git("rev-parse", "--verify", "v0.87.0^{commit}")
        if rc.returncode != 0:
            raise unittest.SkipTest(
                "v0.87.0 tag unavailable: {0}".format(rc.stderr.strip()))
        cls._tmp087 = Path(tempfile.mkdtemp(prefix="rel089-v087-"))
        ls = _git("ls-tree", "-r", "--name-only", "v0.87.0", "--",
                  _INFRA_PREFIX)
        extracted = []
        for rel in ls.stdout.splitlines():
            rel = rel.strip()
            if not rel.endswith(".py"):
                continue
            dest = cls._tmp087 / rel[len(_INFRA_PREFIX):]
            dest.parent.mkdir(parents=True, exist_ok=True)
            show = _git("show", "v0.87.0:" + rel)
            if show.returncode != 0:
                raise unittest.SkipTest(
                    "git show failed for {0}: {1}"
                    .format(rel, show.stderr.strip()))
            dest.write_text(show.stdout, encoding="utf-8")
            extracted.append(rel[len(_INFRA_PREFIX):])
        for required in ("verify_workflow.py", "closure_chain.py",
                         "loop_event_log.py", "archive.py"):
            if required not in extracted:
                raise unittest.SkipTest(
                    "v0.87.0 tree missing {0} (repo={1}, ls rc={2}, "
                    "py={3}, extracted={4})".format(
                        required, _REPO_ROOT, ls.returncode,
                        len([l for l in ls.stdout.splitlines()
                             if l.strip().endswith(".py")]),
                        len(extracted)))

    def _run_087(self, script, *args):
        return subprocess.run(
            [sys.executable, "-c", script, *(str(a) for a in args)],
            cwd=str(self._tmp087), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=300)

    # ── (a) guard 台账：0.87 加载器读 0.88 写入的状态基线 ────────────────

    def test_087_loader_accepts_088_written_state_file(self):
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"
            _seed_gov_rows(gov)
            with mock.patch.object(vw, "GOVERNANCE_DIR", gov), \
                 mock.patch.object(vw, "SAMPLE_PATH",
                                   gov / "plan-tracker.md"):
                result = vw.check_governance_write_shapes(
                    persist_state=True)
            failed = sorted(k for k, f in result.items()
                            if isinstance(f, dict)
                            and f.get("status") == "FAIL")
            self.assertEqual(failed, [], result)
            state_path = gov / ".write-guard-state.json"
            self.assertTrue(state_path.is_file())
            written = json.loads(state_path.read_text(encoding="utf-8"))
            # 0.88 写入器产出 ⊇ 0.87 已知 3 键形状；0.88 增量键 = updated_at
            # （REL-089 实测——0.87 加载器仅校验 schema_version/files，
            # 未知键容忍，schema 兼容成立；增量键如实披露于报告）
            self.assertLessEqual(
                {"schema_version", "tool", "files"},
                set(written.keys()))
            self.assertLessEqual(
                set(written.keys()),
                {"schema_version", "tool", "files", "updated_at"})
            self.assertEqual(written["schema_version"], 1)
            script = (
                "import json, sys, pathlib\n"
                "import verify_workflow as v\n"
                "st, issue = v._load_write_guard_state(pathlib.Path(sys.argv[1]))\n"
                "print(json.dumps({'schema_087': v._WRITE_GUARD_STATE_SCHEMA_VERSION,"
                " 'ok': issue is None, 'schema': st.get('schema_version'),"
                " 'files': sorted(st.get('files', {}).keys()),"
                " 'issue': issue}, ensure_ascii=False))\n"
            )
            proc = self._run_087(script, gov)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            out = json.loads(proc.stdout)
            self.assertEqual(out["schema_087"], 1)      # 双版 schema 恒等
            self.assertTrue(out["ok"], out)
            self.assertEqual(out["schema"], 1)
            for surface in ("evidence-log.md", "plan-tracker.md",
                            "decision-log.md",
                            "plan-tracker.md.ops.jsonl"):
                self.assertIn(surface, out["files"], out)

    # ── (b) closure journal：0.87 读取器遇 0.88 新事件类型 ───────────────

    _JOURNAL_SCRIPT = (
        "import json, sys, pathlib\n"
        "import loop_event_log as lel\n"
        "import closure_chain as cc\n"
        "log = pathlib.Path(sys.argv[1]); cid = 'C-REL089'\n"
        "envs = []\n"
        "plan = [('closure_started', 1, None, {'inputs_digest': 'd0'}),\n"
        "        ('closure_ready', 2, 1, {}),\n"
        "        ('closure_cancelled', 3, 2, {'reason': 'rel089 fixture'}),\n"
        "        ('closure_reopened', 4, 3, {'successor': 'C-REL089-A2'}),\n"
        "        ('closure_fenced', 5, 4, {})]\n"
        "for etype, cas, prev, payload in plan:\n"
        "    ev = lel.build_event(cid, etype, cas_version=cas,"
        " from_version=prev, actor='rel089-fixture', payload=payload)\n"
        "    ev['schema_version'] = cc.CLOSURE_SCHEMA_VERSION\n"
        "    envs.append(ev)\n"
        "log.write_text(''.join(json.dumps(e, ensure_ascii=False,"
        " sort_keys=True) + chr(10) for e in envs), encoding='utf-8')\n"
        "events, problems = cc._load_closure_events(log, cid)\n"
        "seq, prev = cc._next_seq(events)\n"
        "raw = [json.loads(x)['cas_version'] for x in"
        " log.read_text(encoding='utf-8').splitlines() if x.strip()]\n"
        "print(json.dumps({'kept': [e['event_type'] for e in events],"
        " 'problems': problems, 'next_seq': [seq, prev],"
        " 'raw_versions': raw}, ensure_ascii=False))\n"
    )

    def test_087_journal_reader_fails_safe_on_088_event_types(self):
        with tempfile.TemporaryDirectory() as td:
            log_path = Path(td) / "closure-events.jsonl"
            proc = self._run_087(self._JOURNAL_SCRIPT, log_path)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            out = json.loads(proc.stdout)
            # fail-safe 读：新类型事件被跳过 + problems 响亮披露（不崩溃）
            self.assertEqual(out["kept"], ["closure_started",
                                           "closure_ready"])
            joined = "\n".join(out["problems"])
            for etype in _EVENT_TYPES_088_ONLY:
                self.assertIn(etype, joined)
                self.assertIn("unknown closure event_type", joined)
            # seq 碰撞向量（实证——rollback 运行手册门禁的依据）：
            # 0.87 视角的下一 seq 恰与文件中已被 0.88 事件占用的 seq 相撞
            self.assertEqual(out["next_seq"][0], 3)
            self.assertIn(3, out["raw_versions"])
            # 原始文件零改动（读路径零写入）
            self.assertEqual(len(out["raw_versions"]), 5)

    # ── (c) archive：0.87 枚举不触碰 archive/.migration ─────────────────

    def test_087_archive_scan_ignores_migration_dir(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            infra = root / "skills" / "software-project-governance" / "infra"
            infra.mkdir(parents=True)
            (infra / "archive.py").write_text(
                (self._tmp087 / "archive.py").read_text(encoding="utf-8"),
                encoding="utf-8")
            gov = root / ".governance"
            arch = gov / "archive"
            for d in ("tasks", "evidence", "decisions", "risks"):
                (arch / d).mkdir(parents=True)
                (arch / d / ("{0}-v0.86.0~v0.87.0.md".format(d))) \
                    .write_text("# header\n| body |\n", encoding="utf-8")
            (arch / "index.md").write_text("# Archive Index\n",
                                           encoding="utf-8")
            mig = arch / ".migration" / "evidence-v0.87.0~v0.88"
            mig.mkdir(parents=True)
            (mig / "journal.json").write_text(
                '{"schema": "archive-big-table-migration/1"}',
                encoding="utf-8")
            (arch / "tasks" / "decoy-not-md.json").write_text("{}",
                                                              encoding="utf-8")
            script = (
                "import json, sys\n"
                "sys.path.insert(0, sys.argv[1])\n"
                "import archive as ar\n"
                "res = {d: [p if isinstance(p, str) else p.name"
                " for p in ar._get_existing_archive_files(d)]\n"
                "        for d in ('tasks', 'evidence', 'decisions', 'risks')}\n"
                "print(json.dumps({'files': res,"
                " 'index_exists': ar._index_path().is_file()},"
                " ensure_ascii=False))\n"
            )
            proc = subprocess.run(
                [sys.executable, "-c", script, str(infra)], cwd=str(root),
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=300)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            out = json.loads(proc.stdout)
            joined = json.dumps(out)
            self.assertNotIn(".migration", joined)
            self.assertNotIn("journal", joined)
            for d in ("tasks", "evidence", "decisions", "risks"):
                self.assertEqual(out["files"][d],
                                 ["{0}-v0.86.0~v0.87.0.md".format(d)],
                                 out)
            self.assertTrue(out["index_exists"])
            # 0.87 读路径零消费：迁移工件原样在场
            self.assertTrue((mig / "journal.json").is_file())

    # ── 静态证明：v0.87.0 infra 代码对 0.88 新工件零引用 ─────────────────

    def test_087_infra_code_never_references_088_artifacts(self):
        for name in _ARTIFACTS_UNKNOWN_TO_087:
            r = _git("grep", "-l", "-F", name, "v0.87.0", "--",
                     _INFRA_PREFIX)
            if r.returncode not in (0, 1):
                self.fail("git grep failed for {0}: {1}"
                          .format(name, r.stderr.strip()))
            hits = [line.split(":", 1)[-1]
                    for line in r.stdout.splitlines() if line.strip()]
            code_hits = [h for h in hits
                         if h.endswith(".py") and "/tests/" not in h]
            self.assertEqual(code_hits, [],
                             "v0.87.0 infra code references {0}: {1}"
                             .format(name, code_hits))

    def test_087_state_file_reader_is_the_only_shared_artifact_reader(self):
        r = _git("grep", "-l", "-F", ".write-guard-state.json", "v0.87.0",
                 "--", _INFRA_PREFIX)
        self.assertEqual(r.returncode, 0, r.stderr)
        code_hits = [line.split(":", 1)[-1][len(_INFRA_PREFIX):]
                     for line in r.stdout.splitlines() if line.strip()
                     if line.split(":", 1)[-1].endswith(".py")
                     and "/tests/" not in line]
        self.assertEqual(code_hits, ["verify_workflow.py"], code_hits)


if __name__ == "__main__":
    unittest.main()
