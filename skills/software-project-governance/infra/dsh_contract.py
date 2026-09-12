"""Read-only accessor for the dsh host-dependency contract.

FEAT-029 (0.81.0 slice V1) — design §2.5.1 / ADR-018 D-1:

    ``adapters/dsh/host-contract.json`` is the single machine-readable source of
    the dsh host facts this plugin consumes. This module loads it, validates it
    minimally, and hands out read-only values. It performs **no host probing**
    (no ambient setting is consulted, no child process is started, no directory
    outside the one contract file is walked) and it never writes: the only
    writer of the contract is ``dsh-doctor --record-evidence`` (design §2.7, V8).

Public surface (§2.5.1 — four APIs, three exception classes):

    ``CONTRACT_REL``              repo-relative contract path
    ``SUPPORTED_SCHEMA_VERSIONS`` closed set of accepted ``schema_version``
    ``contract_path(root=None)``  absolute path of the contract
    ``load_contract(root=None, *, raw=None)`` -> dict
    ``get(path, contract=None)``  dotted / bracketed path lookup
    ``reset_cache()``             drop the memoized document (tests)

    ``ContractUnreadable``        file missing or unreadable
    ``ContractMalformed``         unparsable / non-object / missing field / bad path
    ``ContractSchemaUnknown``     ``schema_version`` outside the supported set

Failure classification is the vocabulary the boundary check (K-1, V8) reuses —
``ContractMalformed`` is a product defect and MUST NOT be downgraded to
``NOT_RUN`` by a consumer, while ``ContractUnreadable`` may degrade (design
§2.5.1). Error messages always carry the contract path, the exception class and
the offending field/path, so a remediation is actionable.

Two structural rules the design fixes explicitly:

  * **R0 F-5** — the recorded sub-block of every ``host.rows[]`` entry
    (``schema_export`` / ``required_keys`` / ``accepted_keys`` /
    ``probe_result``) may be empty in V1, but it must be *present* and flagged
    ``source: recorded`` / ``recorded: false``. Hand-transcribing schema shapes
    would turn the contract into a second source of truth, so the accessor
    accepts empty and rejects nothing else — filling it is the job of V8.
  * **R0 F-15** — this module MUST NOT import ``registry``: the boundary check
    resolves guard references inside itself, otherwise
    ``registry → checks.dsh_boundary → dsh_contract → registry`` is a cycle
    (ADR-018 §8). Only the standard library is imported.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

__all__ = [
    "CONTRACT_REL",
    "SUPPORTED_SCHEMA_VERSIONS",
    "ContractError",
    "ContractUnreadable",
    "ContractMalformed",
    "ContractSchemaUnknown",
    "contract_path",
    "load_contract",
    "get",
    "reset_cache",
]

#: Contract location, relative to the package root (design §2.3 D-2).
CONTRACT_REL = "adapters/dsh/host-contract.json"

#: Closed set of accepted `schema_version` values (design §2.5.1). An unknown
#: version is fail-closed everywhere: never parse it with old assumptions.
SUPPORTED_SCHEMA_VERSIONS: Tuple[int, ...] = (1,)

#: The eight fields §2.4 requires on every `host.rows[]` entry.
_ROW_FIELDS = ("row_id", "package", "disabled_expr", "platform_conditional",
               "enabled_on", "config_keys", "config_declared", "group")

#: The recorded sub-block (§2.4, R0 F-5): present, flagged, empty in V1.
_RECORDED_FIELDS = ("schema_export", "required_keys", "accepted_keys",
                    "probe_result")

#: Field table of §2.4, flattened to dotted paths. Presence is required; a
#: `null` value is a legitimate "declared but not yet recorded/adjudicated".
REQUIRED_PATHS: Tuple[str, ...] = (
    "schema_version",
    "evidence.audit.id",
    "evidence.audit.path",
    "evidence.audit.head",
    "evidence.audit.date",
    "evidence.recorded_on",
    "evidence.verified_on",
    "evidence.verified_on_ttl_days",
    "evidence.plane.source",
    "evidence.plane.node_modules",
    "evidence.dsh_cli_version",
    "evidence.oracle_packages",
    "evidence.compat_range",
    "evidence.recording.source",
    "evidence.recording.recorded",
    "host.install.scope",
    "host.install.cli_package",
    "host.install.anchor_rel",
    "host.install.env_overrides",
    "host.install.profiles_dir_name",
    "host.install.plane_layout",
    "host.env.home_var",
    "host.env.write_side.blank_policy",
    "host.env.write_side.trim_policy",
    "host.env.write_side.fallback",
    "host.env.write_side.tilde_expansion",
    "host.env.probe_side.require_explicit",
    "host.env.probe_side.no_fallback",
    "host.home.user_preset_dir",
    "host.home.composition_file",
    "host.home.composition_globs",
    "host.row_contract.id_field",
    "host.row_contract.name_field",
    "host.row_contract.config_field",
    "host.row_contract.group_field",
    "host.row_contract.disabled_field",
    "host.row_contract.builtin_prefix",
    "host.row_contract.builtin_group_name",
    "host.row_contract.js_dialect_tag",
    "host.row_contract.loader_scope",
    "host.row_contract.loader_scope_baseurl_shape",
    "host.row_contract.group_self_disabled_shortcircuit",
    "host.row_contract.ancestor_disabled_inherited",
    "host.row_contract.ctx_logger",
    "host.rows",
    "host.skill_frontmatter.name_equals_filename",
    "host.skill_frontmatter.description_required",
    "host.skill_frontmatter.fence",
    "host.apis",
    "host.cli.version_command",
    "host.cli.dump_config_command",
    "host.cli.plugin_command",
    "host.cli.probe_invocation",
    "host.host_plane_registries.registries",
    "host.host_plane_registries.verification",
    "host.notes.profile_declaration",
    "own.package.name",
    "own.package.type",
    "own.package.main",
    "own.package.exports",
    "own.package.files",
    "own.package.engines_node",
    "own.package.dsh_bundle_patch_key",
    "own.host_row.entry",
    "own.host_row.export_surface",
    "own.host_row.apply_never_throws",
    "own.host_row.warn_only",
    "own.host_row.top_level_io",
    "own.host_row.runtime_dependencies",
    "own.patch.file",
    "own.patch.shape_invariants",
    "own.preset.id",
    "own.preset.payload_dir",
    "own.preset.template",
    "own.preset.metadata",
    "own.preset.version_marker",
    "own.preset.skill_root_marker",
    "own.preset.write_policy",
    "own.render.tokens",
    "own.render.newline_policy",
    "own.render.leftover_scan",
    "own.render.custom_skill_dirs_shape",
    "own.paths.host_row",
    "own.paths.launcher",
    "own.paths.guard",
    "own.paths.accessor",
    "own.paths.doctor",
    "own.paths.manifest",
    "own.paths.hooks",
    "own.paths.skill_shims_dir",
    "own.paths_pending",
    "own.adapter_manifest.required_fields",
    "own.checks.smoke_section_title",
    "own.checks.compat_section_title",
    "own.checks.upgrade_regression_label",
    "own.checks.exit_codes",
    "own.notes",
    "coverage.entries",
    "elimination.audit_baseline.total",
    "elimination.audit_baseline.necessary_ids",
    "elimination.audit_baseline.weakenable_ids",
    "elimination.audit_baseline.eliminable_ids",
    "elimination.audit_baseline.historical_ids",
    "elimination.audit_baseline.count_reconciliation",
    "elimination.dispositions",
    "elimination.notes",
)

_MISSING = object()
_CACHE: Dict[str, Dict[str, Any]] = {}


class ContractError(Exception):
    """Base class of the contract's failure vocabulary (§2.5.1)."""


class ContractUnreadable(ContractError):
    """The contract file is absent or cannot be read."""


class ContractMalformed(ContractError):
    """The contract is unparsable, not an object, or misses required fields.

    Also raised by :func:`get` for an undeclared path: "the contract does not
    declare this field" belongs to the same class as "this field is missing".
    """


class ContractSchemaUnknown(ContractError):
    """``schema_version`` is outside :data:`SUPPORTED_SCHEMA_VERSIONS`."""


def _package_root() -> Path:
    """The package root, derived from this module's own location.

    Mirrors the JS side's ``packageRoot()`` (``new URL('..', import.meta.url)``):
    never the process CWD, never an ambient setting.
    """
    return Path(__file__).resolve().parents[3]


def contract_path(root: Optional[Path] = None) -> Path:
    """Absolute path of the host contract under ``root`` (default: package root)."""
    base = Path(root) if root is not None else _package_root()
    return base / CONTRACT_REL


def _fail_unreadable(path: Path, detail: str) -> "ContractUnreadable":
    return ContractUnreadable(
        f"ContractUnreadable: cannot read the host contract: {detail} "
        f"({path})")


def _fail_malformed(path: Path, detail: str) -> "ContractMalformed":
    return ContractMalformed(
        f"ContractMalformed: {detail} in contract {path}")


def _tokenize(path: str) -> List[Tuple[str, Any]]:
    """Split ``a.b[0].c`` / ``host.rows[persona].config_keys`` into tokens."""
    tokens: List[Tuple[str, Any]] = []
    buffer = ""
    index = 0
    while index < len(path):
        char = path[index]
        if char == ".":
            if buffer:
                tokens.append(("key", buffer))
                buffer = ""
            index += 1
            continue
        if char == "[":
            if buffer:
                tokens.append(("key", buffer))
                buffer = ""
            closing = path.find("]", index)
            if closing < 0:
                raise ValueError(f"unbalanced '[' in path {path!r}")
            raw = path[index + 1:closing].strip().strip("'\"")
            tokens.append(("index", int(raw)) if raw.isdigit()
                          else ("key", raw))
            index = closing + 1
            continue
        buffer += char
        index += 1
    if buffer:
        tokens.append(("key", buffer))
    return tokens


def _resolve(document: Any, path: str) -> Any:
    """Resolve ``path``; return :data:`_MISSING` when it is not declared.

    ``[<row id>]`` indexes a list of row objects by their ``row_id`` (the
    spelling §2.4/§4.1 use for coverage subjects), ``[<n>]`` indexes by
    position and ``[<key>]`` indexes a mapping.
    """
    node = document
    try:
        tokens = _tokenize(path)
    except ValueError:
        return _MISSING
    for kind, key in tokens:
        if kind == "index":
            if isinstance(node, list) and 0 <= key < len(node):
                node = node[key]
                continue
            return _MISSING
        if isinstance(node, dict):
            node = node.get(key, _MISSING)
        elif isinstance(node, list):
            found = _MISSING
            for item in node:
                if isinstance(item, dict) and item.get("row_id") == key:
                    found = item
                    break
            node = found
        else:
            return _MISSING
        if node is _MISSING:
            return _MISSING
    return node


def _validate(document: Any, path: Path) -> None:
    if not isinstance(document, dict):
        raise _fail_malformed(path, "the document must be a JSON object")
    for dotted in REQUIRED_PATHS:
        if _resolve(document, dotted) is _MISSING:
            raise _fail_malformed(path, f"missing required field `{dotted}`")
    rows = document["host"]["rows"]
    if not isinstance(rows, list) or not rows:
        raise _fail_malformed(path, "`host.rows` must be a non-empty list")
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise _fail_malformed(path, "every `host.rows[]` entry must be an object")
        row_id = row.get("row_id")
        if not isinstance(row_id, str) or not row_id:
            raise _fail_malformed(path, "`host.rows[]` entries need a `row_id`")
        for field in _ROW_FIELDS:
            if field not in row:
                raise _fail_malformed(
                    path, f"missing required field `host.rows[{row_id}].{field}`")
        recorded = row.get("recorded")
        if not isinstance(recorded, dict):
            raise _fail_malformed(
                path, f"`host.rows[{row_id}].recorded` must be an object")
        for field in _RECORDED_FIELDS:
            if field not in recorded:
                raise _fail_malformed(
                    path,
                    f"missing required field `host.rows[{row_id}].recorded.{field}`")
        if recorded.get("source") != "recorded":
            raise _fail_malformed(
                path,
                f"`host.rows[{row_id}].recorded.source` must be \"recorded\"")
        if recorded.get("recorded") is not False:
            raise _fail_malformed(
                path,
                f"`host.rows[{row_id}].recorded.recorded` must be false — "
                f"present and exactly `false` in V1 (R0 F-5)")
        if row_id in seen:
            raise _fail_malformed(path, f"duplicate `host.rows[]` row_id `{row_id}`")
        seen.add(row_id)
    entries = document["coverage"]["entries"]
    if not isinstance(entries, list) or not entries:
        raise _fail_malformed(path, "`coverage.entries` must be a non-empty list")
    dispositions = document["elimination"]["dispositions"]
    if not isinstance(dispositions, list) or not dispositions:
        raise _fail_malformed(path, "`elimination.dispositions` must be a non-empty list")
    ttl = document["evidence"]["verified_on_ttl_days"]
    if not isinstance(ttl, int) or isinstance(ttl, bool) or ttl <= 0:
        raise _fail_malformed(
            path, "`evidence.verified_on_ttl_days` must be a positive integer")
    schema_version = document["schema_version"]
    if not isinstance(schema_version, int) or isinstance(schema_version, bool):
        raise _fail_malformed(path, "`schema_version` must be an integer")
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise ContractSchemaUnknown(
            f"ContractSchemaUnknown: unsupported schema_version "
            f"{schema_version!r} (supported: "
            f"{', '.join(str(item) for item in SUPPORTED_SCHEMA_VERSIONS)}) "
            f"in contract {path}")


def load_contract(root: Optional[Path] = None,
                  *, raw: Optional[str] = None) -> Dict[str, Any]:
    """Load + minimally validate the host contract.

    ``raw`` bypasses the file system and the process cache: the text is parsed
    as if it were the contract at :func:`contract_path` (used by the self-check
    tests). Otherwise the file is read once per process and memoized;
    :func:`reset_cache` drops it.

    Never guesses a location and never falls back to an inlined copy: an
    unreadable, malformed or schema-unknown contract is reported, not repaired.
    """
    path = contract_path(root)
    from_file = raw is None
    if from_file:
        cached = _CACHE.get(str(path))
        if cached is not None:
            return cached
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            # §2.5.1 / R0 F-1: undecodable bytes are a *read* failure — a
            # consumer may degrade `ContractUnreadable` to NOT_RUN, whereas
            # `ContractMalformed` would force a FAIL. Never let the raw
            # `UnicodeDecodeError` (a ValueError, not an OSError) escape.
            raise _fail_unreadable(path, f"{type(error).__name__}: {error}")
    try:
        document = json.loads(raw)
    except ValueError as error:
        raise _fail_malformed(path, f"JSON parse error: {error}")
    _validate(document, path)
    if from_file:
        _CACHE[str(path)] = document
    return document


def get(path: str, contract: Optional[Dict[str, Any]] = None) -> Any:
    """Return the value declared at ``path`` (dotted, with ``[key]`` lookups).

    Raises :class:`ContractMalformed` when the contract does not declare the
    path — the same class as a missing required field, because "undeclared" and
    "missing" must not be told apart by consumers.
    """
    document = load_contract() if contract is None else contract
    value = _resolve(document, path)
    if value is _MISSING:
        raise _fail_malformed(
            contract_path(), f"path `{path}` is not declared")
    return value


def reset_cache() -> None:
    """Drop the memoized contract document (tests and long-lived processes)."""
    _CACHE.clear()
