import ast
import json
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


INFRA = Path(__file__).resolve().parents[1]
if str(INFRA) not in sys.path:
    sys.path.insert(0, str(INFRA))

from checks.commit import check_release_lineage
from release.context import RepositoryContext
from release.ledger import event_integrity, validate_release_ledger
from release.projection import build_projection_plan, check_projections, write_projections
from release.schema_validation import validate_schema
from release.quality import probe_quality_tools


def git(root, *args):
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8", check=False
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


class TempRepoMixin:
    def init_repo(self, root):
        git(root, "init")
        git(root, "config", "user.email", "test@example.com")
        git(root, "config", "user.name", "Test")
        (root / "project").mkdir()
        (root / "project/CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
        (root / "docs").mkdir()
        (root / "docs/release.md").write_text("release\n", encoding="utf-8")
        (root / ".governance").mkdir()
        (root / ".governance/evidence-log.md").write_text("evidence\n", encoding="utf-8")
        git(root, "add", ".")
        git(root, "commit", "-m", "base")
        return git(root, "rev-parse", "HEAD")

    def artifacts(self):
        return {
            "changelog": "project/CHANGELOG.md",
            "release_docs": ["docs/release.md"],
            "review_evidence": [".governance/evidence-log.md"],
        }


class ReleaseLedgerTests(unittest.TestCase, TempRepoMixin):
    def test_runtime_schema_validation_fail_closed_matrix(self):
        schema=json.loads((INFRA.parent/"core/release-ledger.schema.json").read_text(encoding="utf-8"))
        base={"schema_version":1,"version":"0.66.0","lifecycle_state":"candidate","provenance":"native",
              "artifacts":{"changelog":"x","release_docs":["x"],"review_evidence":["x"]},
              "trust":{"candidate_commit":{"derivation":"git_commit_adding_path"}},"events":[],
              "effective_state":{"lifecycle_state":"candidate","withdrawn":False,"amendments":[]}}
        variants=[]
        item=dict(base); item.pop("version"); variants.append(item)
        item=json.loads(json.dumps(base)); item["extra"]=True; variants.append(item)
        item=json.loads(json.dumps(base)); item["version"]="not-semver"; variants.append(item)
        item=json.loads(json.dumps(base)); item["schema_version"]="1"; variants.append(item)
        item=json.loads(json.dumps(base)); item["trust"]={}; variants.append(item)
        item=json.loads(json.dumps(base)); item["events"]=[{"id":"x","type":"amendment","recorded_at":"bad",
                                                           "claims":[],"integrity":"sha256:"+"0"*64}]; variants.append(item)
        for payload in variants:
            with self.subTest(payload=payload):
                self.assertTrue(validate_schema(payload,schema))

    def test_rfc3339_rejects_date_only_naive_and_space_separated_values(self):
        schema=json.loads((INFRA.parent/"core/release-ledger.schema.json").read_text(encoding="utf-8"))
        for value in ("2026-07-11", "2026-07-11T12:00:00", "2026-07-11 12:00:00Z"):
            payload={"schema_version":1,"version":"0.66.0","lifecycle_state":"candidate","provenance":"native",
                     "artifacts":{"changelog":"x","release_docs":["x"],"review_evidence":["x"]},
                     "trust":{"candidate_commit":{"derivation":"git_commit_adding_path"}},
                     "events":[{"id":"x","type":"amendment","recorded_at":value,"claims":{},"integrity":"sha256:"+"0"*64}],
                     "effective_state":{"lifecycle_state":"candidate","withdrawn":False,"amendments":[]}}
            with self.subTest(value=value):
                self.assertTrue(any("date-time" in issue for issue in validate_schema(payload,schema)))
    def test_historical_manifest_is_historical_only_and_git_derived(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original = self.init_repo(root)
            releases = root / "skills/software-project-governance/core/releases"
            releases.mkdir(parents=True)
            payload = {
                "schema_version": 1,
                "version": "0.62.0",
                "lifecycle_state": "released",
                "provenance": "historical_backfill",
                "artifacts": self.artifacts(),
                "trust": {
                    "original_release_commit": original,
                    "backfill_commit": {"derivation": "git_commit_adding_path"},
                    "document_contemporaneity": "contemporaneous",
                    "tag_disposition": "missing_requires_decision",
                    "tag_decision": None,
                },
                "events": [],
                "effective_state": {"lifecycle_state": "released", "withdrawn": False, "amendments": []},
            }
            (releases / "0.62.0.json").write_text(json.dumps(payload), encoding="utf-8")
            git(root, "add", ".")
            git(root, "commit", "-m", "backfill")
            result = validate_release_ledger(RepositoryContext(root), manifests_dir=releases, verify_remote=False)
            self.assertEqual(result.state, "PASS", result.issues)
            self.assertEqual(result.facts["manifests"][0]["trust_level"], "HISTORICAL_ONLY")

    def test_historical_missing_tag_requires_disposition(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            original = self.init_repo(root)
            releases = root / "releases"
            releases.mkdir()
            payload = {
                "schema_version": 1, "version": "0.62.0", "lifecycle_state": "released",
                "provenance": "historical_backfill", "artifacts": self.artifacts(),
                "trust": {"original_release_commit": original, "backfill_commit": {"derivation": "git_commit_adding_path"},
                          "document_contemporaneity": "backfilled_after_release"},
                "events": [], "effective_state": {"lifecycle_state": "released", "withdrawn": False, "amendments": []},
            }
            (releases / "0.62.0.json").write_text(json.dumps(payload), encoding="utf-8")
            git(root, "add", "."); git(root, "commit", "-m", "backfill")
            result = validate_release_ledger(RepositoryContext(root), manifests_dir=releases, verify_remote=False)
            self.assertEqual(result.state, "FAIL")
            self.assertTrue(any("tag_disposition" in issue for issue in result.issues))

    def test_historical_authorized_tag_requires_real_decision_mapping(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); original=self.init_repo(root); git(root,"tag","v0.62.0",original)
            releases=root/"releases"; releases.mkdir()
            payload={"schema_version":1,"version":"0.62.0","lifecycle_state":"released","provenance":"historical_backfill",
                     "artifacts":self.artifacts(),"trust":{"original_release_commit":original,
                     "backfill_commit":{"derivation":"git_commit_adding_path"},"document_contemporaneity":"contemporaneous",
                     "tag_disposition":"created_by_decision","tag_decision":"DEC-999"},"events":[],
                     "effective_state":{"lifecycle_state":"released","withdrawn":False,"amendments":[]}}
            (releases/"0.62.0.json").write_text(json.dumps(payload),encoding="utf-8")
            git(root,"add","."); git(root,"commit","-m","backfill")
            rejected=validate_release_ledger(RepositoryContext(root),manifests_dir=releases,verify_remote=False)
            self.assertEqual(rejected.state,"FAIL")
            self.assertTrue(any("does not prove" in issue for issue in rejected.issues))
            payload["trust"]["tag_decision"]="DEC-123"
            (releases/"0.62.0.json").write_text(json.dumps(payload),encoding="utf-8")
            decision_log=root/".governance/decision-log.md"
            valid_record={"decision_id":"DEC-123","action":"approved","version":"0.62.0","commit":original,
                          "tag":"v0.62.0","status":"approved"}
            invalid_lines=[
                "HISTORICAL_TAG_AUTHORIZATION_JSON: "+json.dumps(valid_record)+" trailing prose",
                "\n".join(["HISTORICAL_TAG_AUTHORIZATION_JSON: "+json.dumps(valid_record)]*2),
                "HISTORICAL_TAG_AUTHORIZATION_JSON: "+json.dumps({**valid_record,"status":"rejected"}),
                "HISTORICAL_TAG_AUTHORIZATION_JSON: "+json.dumps({**valid_record,"extra":"unknown"}),
            ]
            for line in invalid_lines:
                decision_log.write_text(line+"\n",encoding="utf-8")
                negated=validate_release_ledger(RepositoryContext(root),manifests_dir=releases,verify_remote=False)
                self.assertEqual(negated.state,"FAIL",line)
            decision_log.write_text(
                "HISTORICAL_TAG_AUTHORIZATION_JSON: "+json.dumps(valid_record)+"\n",encoding="utf-8")
            accepted=validate_release_ledger(RepositoryContext(root),manifests_dir=releases,verify_remote=False)
            self.assertEqual(accepted.state,"PASS",accepted.issues)

    def test_missing_requires_decision_rejects_non_null_decision(self):
        schema=json.loads((INFRA.parent/"core/release-ledger.schema.json").read_text(encoding="utf-8"))
        payload={"schema_version":1,"version":"0.62.0","lifecycle_state":"released","provenance":"historical_backfill",
                 "artifacts":{"changelog":"x","release_docs":["x"],"review_evidence":["x"]},
                 "trust":{"original_release_commit":"a"*40,"backfill_commit":"b"*40,
                          "document_contemporaneity":"contemporaneous","tag_disposition":"missing_requires_decision",
                          "tag_decision":"DEC-999"},"events":[],
                 "effective_state":{"lifecycle_state":"released","withdrawn":False,"amendments":[]}}
        self.assertTrue(validate_schema(payload,schema))

    def test_native_candidate_and_unique_release_transition_with_bare_origin(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            root = parent / "work"; root.mkdir()
            bare = parent / "origin.git"
            git(parent, "init", "--bare", str(bare))
            self.init_repo(root)
            git(root, "remote", "add", "origin", str(bare))
            releases = root / "skills/software-project-governance/core/releases"
            releases.mkdir(parents=True)
            manifest = releases / "0.66.0.json"
            candidate = {
                "schema_version": 1, "version": "0.66.0", "lifecycle_state": "candidate", "provenance": "native",
                "artifacts": self.artifacts(), "trust": {"candidate_commit": {"derivation": "git_commit_adding_path"}},
                "events": [], "effective_state": {"lifecycle_state": "candidate", "withdrawn": False, "amendments": []},
            }
            manifest.write_text(json.dumps(candidate), encoding="utf-8")
            git(root, "add", "."); git(root, "commit", "-m", "candidate")
            candidate_commit = git(root, "rev-parse", "HEAD")
            candidate_result = validate_release_ledger(RepositoryContext(root), manifests_dir=releases, verify_remote=False)
            self.assertEqual(candidate_result.state, "PASS", candidate_result.issues)

            event = {"id": "release-0.66.0", "type": "candidate_to_released", "recorded_at": "2026-07-11T12:00:00Z",
                     "claims": {"candidate_parent": candidate_commit}}
            event["integrity"] = event_integrity(event)
            candidate["lifecycle_state"] = "released"
            candidate["events"] = [event]
            candidate["effective_state"]["lifecycle_state"] = "released"
            manifest.write_text(json.dumps(candidate), encoding="utf-8")
            git(root, "add", "."); git(root, "commit", "-m", "release")
            release_commit = git(root, "rev-parse", "HEAD")
            git(root, "tag", "-a", "v0.66.0", "-m", "release")
            git(root, "push", "origin", "HEAD:refs/heads/main", "refs/tags/v0.66.0")
            released = validate_release_ledger(RepositoryContext(root), manifests_dir=releases)
            self.assertEqual(released.state, "PASS", released.issues)
            self.assertEqual(released.facts["manifests"][0]["release_commit"], release_commit)

    def test_release_transition_rejects_non_candidate_parent(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); self.init_repo(root)
            releases = root / "releases"; releases.mkdir()
            manifest = releases / "0.66.0.json"
            candidate = {"schema_version":1,"version":"0.66.0","lifecycle_state":"candidate","provenance":"native",
                         "artifacts":self.artifacts(),"trust":{"candidate_commit":{"derivation":"git_commit_adding_path"}},
                         "events":[],"effective_state":{"lifecycle_state":"candidate","withdrawn":False,"amendments":[]}}
            manifest.write_text(json.dumps(candidate), encoding="utf-8")
            git(root,"add","."); git(root,"commit","-m","candidate")
            (root / "intermediate").write_text("x", encoding="utf-8")
            git(root,"add","."); git(root,"commit","-m","intermediate")
            event={"id":"r","type":"candidate_to_released","recorded_at":"2026-07-11T12:00:00Z","claims":{}}
            event["integrity"]=event_integrity(event)
            candidate["lifecycle_state"]="released"; candidate["events"]=[event]; candidate["effective_state"]["lifecycle_state"]="released"
            manifest.write_text(json.dumps(candidate), encoding="utf-8")
            git(root,"add","."); git(root,"commit","-m","release")
            result=validate_release_ledger(RepositoryContext(root), manifests_dir=releases, verify_remote=False)
            self.assertEqual(result.state,"FAIL")
            self.assertTrue(any("parent" in issue for issue in result.issues))

    def test_event_integrity_and_order_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.init_repo(root); releases=root/"releases"; releases.mkdir()
            events=[]
            for event_id in ("b", "a"):
                event={"id":event_id,"type":"amendment","recorded_at":"2026-07-11T12:00:00Z","claims":{"id":event_id}}
                event["integrity"]=event_integrity(event); events.append(event)
            payload={"schema_version":1,"version":"0.66.0","lifecycle_state":"candidate","provenance":"native",
                     "artifacts":self.artifacts(),"trust":{"candidate_commit":{"derivation":"git_commit_adding_path"}},
                     "events":events,"effective_state":{"lifecycle_state":"candidate","withdrawn":False,
                                                        "amendments":[{"id":"b"},{"id":"a"}]}}
            (releases/"0.66.0.json").write_text(json.dumps(payload),encoding="utf-8")
            git(root,"add","."); git(root,"commit","-m","candidate")
            result=validate_release_ledger(RepositoryContext(root), manifests_dir=releases, verify_remote=False)
            self.assertEqual(result.state,"FAIL")
            self.assertTrue(any("stable" in issue for issue in result.issues))
            payload["events"][0]["claims"]={"tampered":True}
            (releases/"0.66.0.json").write_text(json.dumps(payload),encoding="utf-8")
            result=validate_release_ledger(RepositoryContext(root), manifests_dir=releases, verify_remote=False)
            self.assertTrue(any("integrity hash mismatch" in issue for issue in result.issues))

    def test_shallow_missing_candidate_history_is_unknown(self):
        with tempfile.TemporaryDirectory() as td:
            parent=Path(td); source=parent/"source"; source.mkdir(); self.init_repo(source)
            releases=source/"releases"; releases.mkdir()
            manifest=releases/"0.66.0.json"
            candidate={"schema_version":1,"version":"0.66.0","lifecycle_state":"candidate","provenance":"native",
                       "artifacts":self.artifacts(),"trust":{"candidate_commit":{"derivation":"git_commit_adding_path"}},
                       "events":[],"effective_state":{"lifecycle_state":"candidate","withdrawn":False,"amendments":[]}}
            manifest.write_text(json.dumps(candidate),encoding="utf-8")
            git(source,"add","."); git(source,"commit","-m","candidate"); candidate_commit=git(source,"rev-parse","HEAD")
            event={"id":"r","type":"candidate_to_released","recorded_at":"2026-07-11T12:00:00Z","claims":{}}
            event["integrity"]=event_integrity(event)
            candidate["lifecycle_state"]="released"; candidate["events"]=[event]; candidate["effective_state"]["lifecycle_state"]="released"
            manifest.write_text(json.dumps(candidate),encoding="utf-8")
            git(source,"add","."); git(source,"commit","-m","release")
            shallow=parent/"shallow"
            git(parent,"clone","--depth","1",source.as_uri(),str(shallow))
            result=validate_release_ledger(RepositoryContext(shallow), manifests_dir=shallow/"releases", verify_remote=False)
            self.assertEqual(result.state,"UNKNOWN",result.issues)

    def test_unknown_schema_major_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.init_repo(root); releases=root/"releases"; releases.mkdir()
            (releases/"0.66.0.json").write_text(json.dumps({"schema_version":2,"version":"0.66.0"}),encoding="utf-8")
            result=validate_release_ledger(RepositoryContext(root), manifests_dir=releases, verify_remote=False)
            self.assertEqual(result.state,"BLOCKED")

    def test_legacy_lineage_candidate_compatibility(self):
        result = check_release_lineage("0.65.3", mode="candidate")
        self.assertTrue(result["pass"])
        self.assertEqual(result["state"], "PASS")

    def test_remote_identity_is_blocked_without_echoing_secret(self):
        result = check_release_lineage("0.65.3", mode="released", release_commit="HEAD", remote="https://u:p@example/x")
        self.assertEqual(result["state"], "BLOCKED")
        self.assertNotIn("u:p", json.dumps(result))


class ProjectionTests(unittest.TestCase):
    def fixture(self, root):
        (root / "skills/software-project-governance").mkdir(parents=True)
        (root / "skills/software-project-governance/core").mkdir()
        (root / "skills/software-project-governance/SKILL.md").write_text("---\nversion: 1.2.3\n---\nbody\n", encoding="utf-8")
        (root / "target.json").write_text('{"version":"0.0.0"}\n', encoding="utf-8")
        (root / "target.txt").write_text("version=0.0.0\n", encoding="utf-8")
        (root / "source.bin").write_bytes(b"source\n")
        (root / "target.bin").write_bytes(b"old\n")
        (root / "inventory.py").write_text(
            "REQUIRED_SNIPPETS = {'x': ['required-marker']}\nPROJECTION_SYNC_PATTERNS = ('mirror-pattern',)\n",
            encoding="utf-8")
        contract={"projection_ids":["json","text","zcode-plugin"],
                  "projection_kinds":["byte_copy","structured_json","transformed_text"],
                  "validation_inventories":[
                      {"id":"required-snippets","source":"inventory.py","symbol":"REQUIRED_SNIPPETS",
                       "value_type":"dict","min_entries":1,"required_members":["required-marker"]},
                      {"id":"fixture-mirror-patterns","source":"inventory.py","symbol":"PROJECTION_SYNC_PATTERNS",
                       "value_type":"sequence","min_entries":1,"member_match":"exact",
                       "required_members":["mirror-pattern"]}]}
        (root/"skills/software-project-governance/core/manifest.json").write_text(
            json.dumps({"release_projection_contract":contract}),encoding="utf-8")
        config = {"schema_version":1,"authority":{"kind":"skill_frontmatter_version","path":"skills/software-project-governance/SKILL.md"},
                  "validation_inventories":[{"id":"required-snippets","source":"inventory.py","symbol":"REQUIRED_SNIPPETS"},
                                            {"id":"fixture-mirror-patterns","source":"inventory.py","symbol":"PROJECTION_SYNC_PATTERNS"}],
                  "projections":[
                      {"id":"json","kind":"structured_json","target":"target.json","pointer":"/version"},
                      {"id":"text","kind":"transformed_text","target":"target.txt","pattern":"version=[0-9.]+","replacement":"version={version}","count":1},
                      {"id":"zcode-plugin","kind":"byte_copy","source":"source.bin","target":"target.bin"}]}
        (root / "config.json").write_text(json.dumps(config), encoding="utf-8")

    def test_check_then_write_is_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.fixture(root)
            self.assertEqual(check_projections(root, root/"config.json").state,"FAIL")
            result=write_projections(root, root/"config.json")
            self.assertEqual(result.state,"PASS",result.issues)
            self.assertEqual(check_projections(root, root/"config.json").state,"PASS")
            self.assertEqual(write_projections(root, root/"config.json").facts["written"],0)

    def test_crlf_semantic_match_is_noop_without_journal_or_mtime_change(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.fixture(root)
            first=write_projections(root,root/"config.json")
            self.assertEqual(first.state,"PASS",first.issues)
            for relative in ("target.json","target.txt"):
                path=root/relative
                path.write_bytes(path.read_bytes().replace(b"\n",b"\r\n"))
            before={relative:((root/relative).read_bytes(),(root/relative).stat().st_mtime_ns)
                    for relative in ("target.json","target.txt","target.bin")}
            self.assertEqual(check_projections(root,root/"config.json").state,"PASS")
            result=write_projections(root,root/"config.json")
            self.assertEqual(result.state,"PASS",result.issues)
            self.assertEqual(result.facts["written"],0)
            after={relative:((root/relative).read_bytes(),(root/relative).stat().st_mtime_ns)
                   for relative in before}
            self.assertEqual(after,before)
            self.assertEqual(list(root.glob("spg-projection-*")),[])

    def test_byte_copy_crlf_difference_requires_exact_rewrite(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.fixture(root)
            self.assertEqual(write_projections(root,root/"config.json").state,"PASS")
            (root/"source.bin").write_bytes(b"source\n")
            (root/"target.bin").write_bytes(b"source\r\n")

            checked=check_projections(root,root/"config.json")
            self.assertEqual(checked.state,"FAIL")
            self.assertEqual(checked.issues,["projection drift: target.bin"])

            written=write_projections(root,root/"config.json")
            self.assertEqual(written.state,"PASS",written.issues)
            self.assertEqual(written.facts["written"],1)
            self.assertEqual((root/"target.bin").read_bytes(),b"source\n")

    def test_real_projection_plan_check_then_write_is_raw_noop(self):
        root=INFRA.parents[2]
        version,plan=build_projection_plan(root)
        snapshots={write.relative_path:((root/write.relative_path).read_bytes(),
                                        (root/write.relative_path).stat().st_mtime_ns)
                   for write in plan}
        try:
            self.assertEqual(check_projections(root).state,"PASS")
            result=write_projections(root)
            self.assertEqual(result.state,"PASS",result.issues)
            self.assertEqual(result.facts["written"],0)
            observed={relative:((root/relative).read_bytes(),(root/relative).stat().st_mtime_ns)
                      for relative in snapshots}
            self.assertEqual(observed,snapshots)
        finally:
            for relative,(content,mtime_ns) in snapshots.items():
                path=root/relative
                if path.read_bytes()!=content:
                    path.write_bytes(content)
                os.utime(path,ns=(path.stat().st_atime_ns,mtime_ns))

    def test_write_rolls_back_every_target_on_replace_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.fixture(root)
            before={p.name:p.read_bytes() for p in (root/"target.json",root/"target.txt",root/"target.bin")}
            calls={"count":0,"failed":False}
            def flaky(source,target):
                calls["count"]+=1
                if calls["count"]==2 and not calls["failed"]:
                    calls["failed"]=True
                    raise OSError("boom")
                os.replace(source,target)
            result=write_projections(root,root/"config.json",replace=flaky)
            self.assertEqual(result.state,"FAIL",result.issues)
            after={p.name:p.read_bytes() for p in (root/"target.json",root/"target.txt",root/"target.bin")}
            self.assertEqual(after,before)

    def test_incomplete_rollback_preserves_executable_recovery_materials(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.fixture(root)
            calls={"count":0}
            def broken(source,target):
                calls["count"]+=1
                if calls["count"] >= 2:
                    raise OSError("apply and rollback failure")
                os.replace(source,target)
            result=write_projections(root,root/"config.json",replace=broken)
            self.assertEqual(result.state,"BLOCKED",result.issues)
            journal_dir=Path(result.facts["rollback_journal"])
            self.assertTrue((journal_dir/"journal.json").is_file())
            journal=json.loads((journal_dir/"journal.json").read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(journal["entries"]),3)
            for index, entry in enumerate(journal["entries"]):
                self.assertTrue((journal_dir/entry["backup"]).is_file())
                self.assertTrue((journal_dir/f"{index}.staged").is_file())

    def test_path_traversal_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.fixture(root)
            config=json.loads((root/"config.json").read_text())
            config["projections"][0]["target"]="../outside.json"
            (root/"config.json").write_text(json.dumps(config),encoding="utf-8")
            self.assertEqual(check_projections(root,root/"config.json").state,"BLOCKED")


    def test_conflicting_target_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.fixture(root)
            config=json.loads((root/"config.json").read_text())
            config["projections"].append(dict(config["projections"][0]))
            (root/"config.json").write_text(json.dumps(config),encoding="utf-8")
            self.assertEqual(check_projections(root,root/"config.json").state,"BLOCKED")

    def test_missing_required_projection_id_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.fixture(root)
            config=json.loads((root/"config.json").read_text())
            config["projections"]=[item for item in config["projections"] if item["id"] != "zcode-plugin"]
            (root/"config.json").write_text(json.dumps(config),encoding="utf-8")
            result=check_projections(root,root/"config.json")
            self.assertEqual(result.state,"BLOCKED")
            self.assertTrue(any("projection ID contract mismatch" in issue for issue in result.issues))

    def test_empty_or_missing_inventory_content_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.fixture(root)
            (root/"inventory.py").write_text(
                "REQUIRED_SNIPPETS = {}\nPROJECTION_SYNC_PATTERNS = ()\n",encoding="utf-8")
            result=check_projections(root,root/"config.json")
            self.assertEqual(result.state,"BLOCKED")
            self.assertTrue(any("requires at least" in issue for issue in result.issues))

    def test_bad_pointer_regex_count_and_type_are_blocked_without_traceback(self):
        mutations = [
            lambda c: c["projections"][0].update(pointer="/missing"),
            lambda c: c["projections"][1].update(pattern="["),
            lambda c: c["projections"][1].update(count="bad"),
            lambda c: c["projections"][0].update(pointer=42),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as td:
                root=Path(td); self.fixture(root)
                config=json.loads((root/"config.json").read_text()); mutate(config)
                (root/"config.json").write_text(json.dumps(config),encoding="utf-8")
                result=check_projections(root,root/"config.json")
                self.assertEqual(result.state,"BLOCKED",result.issues)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink unsupported")
    def test_symlink_target_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.fixture(root)
            real=root/"real.json"; real.write_text('{"version":"0.0.0"}',encoding="utf-8")
            (root/"target.json").unlink()
            try:
                os.symlink(real,root/"target.json")
            except OSError:
                self.skipTest("symlink creation not permitted")
            self.assertEqual(check_projections(root,root/"config.json").state,"BLOCKED")

    def test_symlink_parent_fact_blocks_build_check_and_write_portably(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.fixture(root)
            nested=root/"nested"; nested.mkdir()
            (nested/"target.json").write_text('{"version":"0.0.0"}\n',encoding="utf-8")
            config=json.loads((root/"config.json").read_text(encoding="utf-8"))
            config["projections"][0]["target"]="nested/target.json"
            (root/"config.json").write_text(json.dumps(config),encoding="utf-8")
            original_is_symlink=Path.is_symlink

            def injected_is_symlink(path):
                if path == nested:
                    return True
                return original_is_symlink(path)

            with mock.patch.object(Path,"is_symlink",autospec=True,side_effect=injected_is_symlink):
                with self.assertRaisesRegex(ValueError,"traverses symlink"):
                    build_projection_plan(root,root/"config.json")
                self.assertEqual(check_projections(root,root/"config.json").state,"BLOCKED")
                self.assertEqual(write_projections(root,root/"config.json").state,"BLOCKED")


class ReleaseModuleBoundaryTests(unittest.TestCase):
    def test_release_modules_do_not_import_or_reexport_verify_workflow(self):
        paths=sorted((INFRA/"release").glob("*.py"))+[
            INFRA/"checks/commit.py",
            INFRA/"checks/version.py",
            INFRA/"checks/projection.py",
        ]
        violations=[]
        for path in paths:
            tree=ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):
                    for alias in node.names:
                        if alias.name=="verify_workflow" or alias.name.endswith(".verify_workflow"):
                            violations.append(f"{path.name}:{node.lineno}: import {alias.name}")
                        if alias.asname=="verify_workflow":
                            violations.append(f"{path.name}:{node.lineno}: re-export alias {alias.asname}")
                elif isinstance(node,ast.ImportFrom):
                    module=node.module or ""
                    if module=="verify_workflow" or module.endswith(".verify_workflow"):
                        violations.append(f"{path.name}:{node.lineno}: from {module} import")
                    for alias in node.names:
                        if alias.name=="verify_workflow" or alias.asname=="verify_workflow":
                            violations.append(
                                f"{path.name}:{node.lineno}: re-export alias {alias.asname or alias.name}"
                            )
        self.assertEqual(violations,[])


class QualityProbeTests(unittest.TestCase):
    def test_uninstalled_tools_are_structured_not_run(self):
        result=probe_quality_tools(which=lambda _name: None)
        self.assertEqual(result["state"],"NOT_RUN")
        self.assertEqual(result["tools"]["ruff"]["state"],"NOT_RUN")
        self.assertFalse(result["runtime_dependency"])

    def test_installed_tool_failure_is_not_pass(self):
        completed=subprocess.CompletedProcess(["tool","--version"],1,"","bad")
        result=probe_quality_tools(which=lambda name:name,runner=lambda *a,**k:completed)
        self.assertEqual(result["state"],"FAIL")
        self.assertTrue(all(item["state"]=="FAIL" for item in result["tools"].values()))


if __name__ == "__main__":
    unittest.main()
