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
    ``is_deprecated(path, contract=None)`` -> bool (v2, see below)
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

Contract v2 (FEAT-113 S0, design §8.2.1) is **additive only**: the new keys
(``own.overlay``, ``own.native.base_preset``, ``own.preset.render_provenance``,
``own.render.persona_prefix``, ``host.planes``, ``host.home.discovery``,
``host.apis.loader_ctx``) join ``REQUIRED_PATHS`` — a missing one is
``ContractMalformed`` — and ``SUPPORTED_SCHEMA_VERSIONS`` becomes ``(2,)``: the
in-package contract ships with its code, so a v1 document is
``ContractSchemaUnknown`` (there is no legal v1 scenario; never parse it with
v2 assumptions).

**Deprecation representation (v2).** ``host.rows`` and ``own.preset.template``
stay in ``REQUIRED_PATHS`` *and* are recorded as deprecated by a sidecar block
in the contract itself — the single source, this module holds no second copy:

    "deprecations": {
      "_note": "...",
      "entries": {"host.rows": {"deprecated_in": 2}, ...}
    }

"Required-but-deprecated" is a distinct state from "optional": a *missing*
deprecated key is still ``ContractMalformed`` (otherwise a reader could not
tell "the new contract" from "a broken contract" — §8.2.1 timing block); only
the deprecation is recorded, and :func:`is_deprecated` reads it back. The
physical removal of both keys is the S7 atomic retirement slice, not S0.
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
    "is_deprecated",
    "reset_cache",
]

#: Contract location, relative to the package root (design §2.3 D-2).
CONTRACT_REL = "adapters/dsh/host-contract.json"

#: Closed set of accepted `schema_version` values (design §2.5.1). An unknown
#: version is fail-closed everywhere: never parse it with old assumptions.
#: v2 (FEAT-113 S0, §8.2.1): the in-package contract ships with its code, so
#: v1 is no longer a legal scenario — reading one raises
#: `ContractSchemaUnknown` instead of being honored as "older but fine".
SUPPORTED_SCHEMA_VERSIONS: Tuple[int, ...] = (2,)

#: The eight fields §2.4 requires on every `host.rows[]` entry.
_ROW_FIELDS = ("row_id", "package", "disabled_expr", "platform_conditional",
               "enabled_on", "config_keys", "config_declared", "group")

#: The recorded sub-block (§2.4, R0 F-5): present, flagged, empty in V1.
_RECORDED_FIELDS = ("schema_export", "required_keys", "accepted_keys",
                    "probe_result")

#: Field table of §2.4, flattened to dotted paths. Presence is required; a
#: `null` value is a legitimate "declared but not yet recorded/adjudicated".
#: v2 (FEAT-113 §8.2.1) appends the new additive keys, and keeps two entries
#: in a deliberately distinct state — "required-but-deprecated": `host.rows`
#: and `own.preset.template` remain listed here (a missing one is malformed)
#: while the `deprecations` sidecar records that each was deprecated in
#: schema 2 (removal is the S7 slice; see `is_deprecated`).
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
    "host.planes.precedence",
    "host.planes.asar.header",
    "host.planes.asar.content_base",
    "host.planes.asar.runner.flag",
    "host.planes.asar.runner.module_flag",
    "host.planes.asar.runtime_rel",
    "host.planes.asar.unpacked_cannot_serve",
    "host.planes.asar.entry_count_cap",
    "host.planes.env.desktop_app_dir",
    "host.planes.env.profile_dir",
    "host.planes.process_probe.enabled_in",
    "host.planes.process_probe.max_ancestors",
    "host.home.user_preset_dir",
    "host.home.composition_file",
    "host.home.composition_globs",
    "host.home.discovery.roots",
    "host.home.discovery.suffixes",
    "host.home.discovery.exclude_names",
    "host.home.discovery.bounds.max_depth",
    "host.home.discovery.bounds.max_entries",
    "host.home.discovery.bounds.max_seconds",
    "host.home.discovery.follow_reparse",
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
    "host.apis.loader_ctx.members",
    "host.apis.loader_ctx.unlisted_member",
    "host.apis.loader_ctx.stub_values",
    "host.apis.loader_ctx.evidence",
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
    "own.overlay.path",
    "own.overlay.rows",
    "own.overlay.persona_body_token",
    "own.overlay.persona_body_source",
    "own.overlay.allow_js",
    "own.preset.id",
    "own.preset.payload_dir",
    "own.preset.template",
    "own.preset.metadata",
    "own.preset.version_marker",
    "own.preset.skill_root_marker",
    "own.preset.write_policy",
    "own.preset.render_provenance.filename",
    "own.preset.render_provenance.schema",
    "own.preset.render_provenance.fields",
    "own.preset.render_provenance.absent_policy",
    "own.native.base_preset.patch_rel",
    "own.native.base_preset.row_selector.name",
    "own.native.base_preset.row_selector.config_id",
    "own.native.base_preset.rows_path",
    "own.native.base_preset.insert_selector",
    "own.render.tokens",
    "own.render.newline_policy",
    "own.render.leftover_scan",
    "own.render.persona_prefix.mode",
    "own.render.persona_prefix.separator",
    "own.render.persona_prefix.trailing",
    "own.render.persona_prefix.empty_prefix",
    "own.render.persona_prefix.body_source",
    "own.render.persona_prefix.body_token",
    "own.render.persona_prefix.body_token_value",
    "own.render.persona_prefix.body_crlf",
    "own.render.persona_prefix.body_trim",
    "own.render.persona_prefix.body_empty_policy",
    "own.render.persona_prefix.leftover_scan",
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
    "deprecations.entries",
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


def _is_name_list(value: Any) -> bool:
    """A non-empty JSON array of non-empty strings (a declared name list)."""
    return (isinstance(value, list) and bool(value)
            and all(isinstance(item, str) and item for item in value))


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
    # ── contract v2 (FEAT-113 §8.2.1): additive keys ──────────────────────
    # Nested shape checks only where the §8.2.1 table constrains the value as
    # a list of declared names — the same style as the `host.apis` guard the
    # compat check applies (fail loud, name the field). Everything else about
    # the new keys is presence-only (REQUIRED_PATHS above), deliberately not
    # over-fitted: the values are normative data, not this module's business.
    overlay_rows = document["own"]["overlay"]["rows"]
    if not _is_name_list(overlay_rows):
        raise _fail_malformed(
            path, "`own.overlay.rows` must be a non-empty list of row ids")
    precedence = document["host"]["planes"]["precedence"]
    if not _is_name_list(precedence):
        raise _fail_malformed(
            path,
            "`host.planes.precedence` must be a non-empty list of "
            "plane sources")
    discovery = document["host"]["home"]["discovery"]
    for field in ("roots", "suffixes"):
        if not _is_name_list(discovery[field]):
            raise _fail_malformed(
                path,
                f"`host.home.discovery.{field}` must be a non-empty "
                f"list of strings")
    members = document["host"]["apis"]["loader_ctx"]["members"]
    if not _is_name_list(members):
        raise _fail_malformed(
            path,
            "`host.apis.loader_ctx.members` must be a non-empty list of "
            "ctx member names")
    # The deprecation sidecar: `entries` maps a dotted contract path to
    # `{deprecated_in: <int>}`. Shape only — which keys may be deprecated is
    # a contract-maintenance fact, not a validation rule.
    deprecations = document["deprecations"]["entries"]
    if not isinstance(deprecations, dict) or not deprecations:
        raise _fail_malformed(
            path, "`deprecations.entries` must be a non-empty object")
    for dotted, entry in deprecations.items():
        field = f"deprecations.entries[{dotted}]"
        if not isinstance(dotted, str) or not dotted:
            raise _fail_malformed(
                path, "`deprecations.entries` keys must be dotted paths")
        if not isinstance(entry, dict):
            raise _fail_malformed(path, f"`{field}` must be an object")
        version = entry.get("deprecated_in")
        if not isinstance(version, int) or isinstance(version, bool):
            raise _fail_malformed(
                path, f"`{field}.deprecated_in` must be an integer")
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


def is_deprecated(path: str,
                  contract: Optional[Dict[str, Any]] = None) -> bool:
    """Whether ``path`` is recorded as deprecated by the contract's sidecar.

    Contract v2 (FEAT-113 S0, §8.2.1): the ``deprecations.entries`` block —
    ``{<dotted path>: {"deprecated_in": <int>}}`` — is the single source of
    this fact; this module keeps no second copy. Deprecation is metadata
    only: a deprecated path is still in :data:`REQUIRED_PATHS`, so a missing
    one is ``ContractMalformed`` ("required-but-deprecated" is a distinct
    state from "optional" — the timing block of §8.2.1). Returns ``False``
    for any path the sidecar does not record.
    """
    document = load_contract() if contract is None else contract
    entries = _resolve(document, "deprecations.entries")
    if not isinstance(entries, dict):
        return False
    entry = entries.get(path)
    version = entry.get("deprecated_in") if isinstance(entry, dict) else None
    return isinstance(version, int) and not isinstance(version, bool)


def reset_cache() -> None:
    """Drop the memoized contract document (tests and long-lived processes)."""
    _CACHE.clear()
