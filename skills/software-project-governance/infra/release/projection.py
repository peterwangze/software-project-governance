"""Deterministic artifact projection check/write engine."""

from copy import deepcopy
from dataclasses import dataclass
import ast
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
from typing import Dict, Iterable, List, Optional

from .model import CheckResult


@dataclass(frozen=True)
class PlannedWrite:
    relative_path: str
    content: bytes
    kind: str


def _projection_matches(write: PlannedWrite, current: bytes) -> bool:
    if write.kind == "byte_copy":
        return current == write.content
    return current.replace(b"\r\n", b"\n") == write.content.replace(b"\r\n", b"\n")


def _inventory_value(source: Path, symbol: str) -> tuple[str, int, set[str]]:
    try:
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    except (OSError, SyntaxError) as exc:
        raise ValueError(f"cannot parse validation inventory source `{source}`: {exc}") from exc
    assignments = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == symbol for target in node.targets):
            assignments.append(node.value)
    if not assignments:
        raise ValueError(f"validation inventory symbol is missing: {symbol}")
    value = assignments[-1]
    if isinstance(value, ast.Dict):
        members = set()
        for item in value.values:
            if not isinstance(item, (ast.List, ast.Tuple)):
                raise ValueError(f"inventory `{symbol}` dictionary values must be literal string sequences")
            for element in item.elts:
                if not isinstance(element, ast.Constant) or not isinstance(element.value, str):
                    raise ValueError(f"inventory `{symbol}` contains a non-literal member")
                members.add(element.value)
        return "dict", len(value.keys), members
    if isinstance(value, (ast.List, ast.Tuple)):
        members = set()
        for element in value.elts:
            if not isinstance(element, ast.Constant) or not isinstance(element.value, str):
                raise ValueError(f"inventory `{symbol}` contains a non-literal member")
            members.add(element.value)
        return "sequence", len(value.elts), members
    raise ValueError(f"inventory `{symbol}` must be a literal dict/list/tuple assignment")


def _safe_repo_path(root: Path, raw: object, *, must_exist: bool = False) -> Path:
    if not isinstance(raw, str) or not raw or "\\" in raw:
        raise ValueError("projection paths must be non-empty repo-relative POSIX paths")
    pure = PurePosixPath(raw)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"unsafe projection path `{raw}`")
    path = root.joinpath(*pure.parts)
    cursor = root
    for part in pure.parts:
        cursor = cursor / part
        if cursor.exists() and cursor.is_symlink():
            raise ValueError(f"projection path traverses symlink `{raw}`")
    if must_exist and not path.is_file():
        raise ValueError(f"projection source is missing `{raw}`")
    return path


def _skill_version(path: Path) -> str:
    match = re.search(r"^version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$", path.read_text(encoding="utf-8"), re.MULTILINE)
    if not match:
        raise ValueError("authoritative SKILL.md frontmatter version is missing")
    return match.group(1)


def _json_pointer_set(payload: object, pointer: str, value: object) -> object:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError(f"invalid JSON pointer `{pointer}`")
    parts = [part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")]
    current = payload
    for part in parts[:-1]:
        if isinstance(current, list):
            current = current[int(part)]
        elif isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise ValueError(f"JSON pointer `{pointer}` does not resolve")
    leaf = parts[-1]
    if isinstance(current, list):
        current[int(leaf)] = value
    elif isinstance(current, dict) and leaf in current:
        current[leaf] = value
    else:
        raise ValueError(f"JSON pointer `{pointer}` does not resolve")
    return payload


def build_projection_plan(root: Path, config_path: Optional[Path] = None) -> tuple[str, List[PlannedWrite]]:
    root = root.resolve()
    config_path = config_path or root / "skills/software-project-governance/core/version-projections.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    manifest_path = root / "skills/software-project-governance/core/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    contract = manifest.get("release_projection_contract")
    if not isinstance(contract, dict):
        raise ValueError("canonical manifest release_projection_contract is required")
    if config.get("schema_version") != 1:
        raise ValueError("unsupported projection schema major")
    projections = config.get("projections")
    inventories = config.get("validation_inventories")
    if not isinstance(projections, list) or not projections:
        raise ValueError("projection registry must contain projections")
    required_ids = contract.get("projection_ids")
    required_kinds = contract.get("projection_kinds")
    required_inventories = contract.get("validation_inventories")
    if not isinstance(required_ids, list) or not required_ids or not all(isinstance(item, str) for item in required_ids):
        raise ValueError("manifest projection_ids must be a non-empty string list")
    if not isinstance(required_kinds, list) or not required_kinds:
        raise ValueError("manifest projection_kinds must be a non-empty list")
    if not isinstance(required_inventories, list) or not required_inventories:
        raise ValueError("manifest validation_inventories must be a non-empty list")
    projection_ids = [item.get("id") for item in projections if isinstance(item, dict)]
    if len(projection_ids) != len(projections) or len(set(projection_ids)) != len(projection_ids):
        raise ValueError("projection IDs must be present and unique")
    if set(required_ids) != set(projection_ids):
        raise ValueError(
            f"projection ID contract mismatch: required={sorted(set(required_ids))}, "
            f"registry={sorted(set(projection_ids))}"
        )
    kinds = {item.get("kind") for item in projections}
    if set(required_kinds) != kinds:
        raise ValueError(f"projection kind contract mismatch: required={sorted(required_kinds)}, registry={sorted(kinds)}")
    if not isinstance(inventories, list):
        raise ValueError("validation inventory declarations are required")
    inventory_contract = {
        (item.get("id"), item.get("source"), item.get("symbol"))
        for item in required_inventories if isinstance(item, dict)
    }
    inventory_registry = {
        (item.get("id"), item.get("source"), item.get("symbol"))
        for item in inventories if isinstance(item, dict)
    }
    if len(inventory_contract) != len(required_inventories) or inventory_contract != inventory_registry:
        raise ValueError("validation inventory contract mismatch")
    contract_by_id = {item["id"]: item for item in required_inventories}
    for inventory in inventories:
        inventory_id = inventory.get("id")
        source = _safe_repo_path(root, inventory.get("source"), must_exist=True)
        symbol = inventory.get("symbol")
        contract_item = contract_by_id[inventory_id]
        value_type, count, members = _inventory_value(source, symbol)
        if value_type != contract_item.get("value_type"):
            raise ValueError(f"validation inventory type mismatch: {inventory_id}")
        minimum = contract_item.get("min_entries")
        if not isinstance(minimum, int) or minimum < 1 or count < minimum:
            raise ValueError(f"validation inventory `{inventory_id}` has {count} entries, requires at least {minimum}")
        required_members = contract_item.get("required_members")
        if not isinstance(required_members, list) or not required_members:
            raise ValueError(f"validation inventory required_members missing: {inventory_id}")
        missing_members = sorted(set(required_members) - members)
        if missing_members:
            raise ValueError(f"validation inventory `{inventory_id}` missing members: {missing_members}")
        if contract_item.get("member_match") == "exact" and members != set(required_members):
            raise ValueError(f"validation inventory `{inventory_id}` has undeclared or missing members")
    authority = config.get("authority", {})
    if authority.get("kind") != "skill_frontmatter_version":
        raise ValueError("SKILL frontmatter must remain the projection authority")
    authority_path = _safe_repo_path(root, authority.get("path"), must_exist=True)
    version = _skill_version(authority_path)

    writes: Dict[str, tuple[bytes, str]] = {}
    for item in projections:
        if not isinstance(item, dict):
            raise ValueError("projection entries must be objects")
        kind = item.get("kind")
        target_rel = item.get("target")
        target = _safe_repo_path(root, target_rel, must_exist=True)
        if target_rel in writes:
            raise ValueError(f"conflicting projection target `{target_rel}`")
        if kind == "byte_copy":
            source = _safe_repo_path(root, item.get("source"), must_exist=True)
            if source == target:
                raise ValueError("byte projection source and target must differ")
            content = source.read_bytes()
        elif kind == "structured_json":
            payload = json.loads(target.read_text(encoding="utf-8"))
            payload = _json_pointer_set(deepcopy(payload), item.get("pointer"), version)
            content = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        elif kind == "transformed_text":
            text = target.read_text(encoding="utf-8")
            pattern = item.get("pattern")
            if not isinstance(pattern, str):
                raise ValueError("transformed_text requires a pattern")
            replacement = str(item.get("replacement", "{version}")).replace("{version}", version)
            transformed, count = re.subn(pattern, replacement, text, count=int(item.get("count", 1)), flags=re.MULTILINE)
            if count != int(item.get("count", 1)):
                raise ValueError(f"projection pattern count mismatch for `{target_rel}`")
            content = transformed.encode("utf-8")
        else:
            raise ValueError(f"unsupported projection kind `{kind}`")
        writes[target_rel] = (content, kind)
    return version, [PlannedWrite(path, writes[path][0], writes[path][1]) for path in sorted(writes)]


def check_projections(root: Path, config_path: Optional[Path] = None) -> CheckResult:
    try:
        version, plan = build_projection_plan(root, config_path)
    except (OSError, ValueError, TypeError, KeyError, IndexError, json.JSONDecodeError, re.error) as exc:
        return CheckResult("BLOCKED", [str(exc)])
    issues = []
    for write in plan:
        path = _safe_repo_path(root.resolve(), write.relative_path, must_exist=True)
        current = path.read_bytes()
        if not _projection_matches(write, current):
            issues.append(f"projection drift: {write.relative_path}")
    return CheckResult(
        "FAIL" if issues else "PASS",
        issues,
        {"source_version": version, "projections_checked": len(plan)},
    )


def write_projections(
    root: Path,
    config_path: Optional[Path] = None,
    *,
    replace=os.replace,
) -> CheckResult:
    root = root.resolve()
    try:
        version, plan = build_projection_plan(root, config_path)
        for write in plan:
            _safe_repo_path(root, write.relative_path, must_exist=True)
    except (OSError, ValueError, TypeError, KeyError, IndexError, json.JSONDecodeError, re.error) as exc:
        return CheckResult("BLOCKED", [str(exc)])

    changed = [
        write for write in plan
        if not _projection_matches(write, (root / write.relative_path).read_bytes())
    ]
    if not changed:
        return CheckResult("PASS", facts={"source_version": version, "written": 0})

    journal_dir = Path(tempfile.mkdtemp(prefix="spg-projection-", dir=str(root)))
    journal = {"version": version, "entries": []}
    staged: Dict[str, Path] = {}
    cleanup_journal = False
    try:
        for index, write in enumerate(changed):
            target = _safe_repo_path(root, write.relative_path, must_exist=True)
            backup = journal_dir / f"{index}.backup"
            staged_path = journal_dir / f"{index}.staged"
            backup.write_bytes(target.read_bytes())
            staged_path.write_bytes(write.content)
            staged[write.relative_path] = staged_path
            journal["entries"].append({"target": write.relative_path, "backup": backup.name})
        (journal_dir / "journal.json").write_text(
            json.dumps(journal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        replaced = []
        for index, write in enumerate(changed):
            target = _safe_repo_path(root, write.relative_path, must_exist=True)
            apply_path = journal_dir / f"{index}.apply"
            shutil.copyfile(staged[write.relative_path], apply_path)
            replace(apply_path, target)
            replaced.append(write.relative_path)
        checked = check_projections(root, config_path)
        if checked.state != "PASS":
            raise OSError("post-write projection validation failed")
        cleanup_journal = True
    except Exception as exc:
        rollback_issues = []
        for entry in reversed(journal["entries"]):
            try:
                backup = journal_dir / entry["backup"]
                target = _safe_repo_path(root, entry["target"], must_exist=True)
                if backup.exists():
                    restore_path = journal_dir / f"restore-{entry['backup']}"
                    shutil.copyfile(backup, restore_path)
                    replace(restore_path, target)
            except Exception as rollback_exc:
                rollback_issues.append(f"rollback failed for {entry['target']}: {type(rollback_exc).__name__}")
        if not rollback_issues:
            cleanup_journal = True
        return CheckResult(
            "BLOCKED" if rollback_issues else "FAIL",
            [f"projection write failed: {type(exc).__name__}", *rollback_issues],
            {"rollback_journal": str(journal_dir)},
        )
    finally:
        if cleanup_journal:
            for path in journal_dir.glob("*"):
                try:
                    path.unlink()
                except OSError:
                    pass
            try:
                journal_dir.rmdir()
            except OSError:
                pass
    return CheckResult("PASS", facts={"source_version": version, "written": len(changed)})
