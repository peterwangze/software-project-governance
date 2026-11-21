"""Derive the directory preset from the installed host without loading YAML code.

Only the two declared overlay fields are rewritten. The host owns the text of
every other row, including comments, loader expressions and nested groups.
"""
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys


class RenderRefused(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(f"{code}: {message}")


def _refuse(code, message):
    raise RenderRefused(code, message)


def verify_payload(target, spec, names):
    """Verify only the known files before diagnosing or replacing a rendered directory."""
    if target.is_symlink() or not target.is_dir() or target.resolve() != target.absolute():
        raise ValueError("preset directory is redirected")
    children = list(target.iterdir())
    expected = set(names) | {spec["filename"]}
    unexpected = {child.name for child in children} ^ expected
    redirected = {child.name for child in children if child.is_symlink() or not child.is_file()}
    if unexpected or redirected:
        raise ValueError("legacy, additional, or redirected files: " +
                         ", ".join(sorted(unexpected | redirected)))
    receipt = json.loads((target / spec["filename"]).read_bytes())
    if not isinstance(receipt, dict) or receipt.get("schema") != spec["schema"]:
        raise ValueError("invalid preset receipt")
    hashes = receipt.get("payload_sha256")
    if not isinstance(hashes, dict) or set(hashes) != set(names):
        raise ValueError("incomplete installed payload receipt")
    edited = [name for name in sorted(names)
              if sha256((target / name).read_bytes()).hexdigest() != hashes[name]]
    if edited:
        raise ValueError("installed payload differs from its receipt: " + ", ".join(edited))
    return receipt


def _content(line):
    return bool(line.strip()) and not line.lstrip().startswith("#")


def _indent(line):
    return len(line) - len(line.lstrip(" "))


def _end(lines, start):
    indentation = _indent(lines[start])
    return next((i for i in range(start + 1, len(lines))
                 if _content(lines[i]) and _indent(lines[i]) <= indentation), len(lines))


def _scalar(text, code):
    text = text.strip()
    if text.startswith("'") and text.endswith("'"):
        return text[1:-1].replace("''", "'")
    if text.startswith('"'):
        try:
            value = json.loads(text)
        except ValueError:
            _refuse(code, "unsupported quoted scalar")
        if isinstance(value, str):
            return value
    if not text or text[0] in "!&*|>{[%" or " #" in text or ": " in text:
        _refuse(code, f"unsupported scalar {text!r}")
    if text.casefold() in {"true", "false", "null", "~"} or re.fullmatch(r"[+-]?[0-9]+(?:\.[0-9]+)?", text):
        _refuse(code, f"expected text, found {text!r}")
    return text


def _rows(lines, indentation, code):
    """Split a block sequence without ever parsing content inside a row."""
    rows = []
    for i, line in enumerate(lines):
        if not _content(line):
            continue
        if line.startswith("\t") or _indent(line) < indentation:
            _refuse(code, "unexpected row indentation")
        if _indent(line) != indentation:
            if not rows:
                _refuse(code, "expected a sequence row beginning with id")
            continue
        match = re.fullmatch(r"- id:\s+(.+?)\s*", line[indentation:])
        if not match:
            _refuse(code, f"expected '- id:' at line {i + 1}")
        key = _scalar(match[1], code)
        if any(item[0] == key for item in rows):
            _refuse(code, f"duplicate row id {key}")
        rows.append((key, i))
    return [(key, [line[indentation:] if line.strip() else "" for line in lines[start:stop]])
            for (key, start), (_, stop) in zip(rows, rows[1:] + [(None, len(lines))])]


def row_ids(composition):
    return [key for key, _ in _rows(composition.splitlines(), 0, "BASE_ROW_INDENT_DRIFT")]


def row_paths(composition):
    """List top-level and nested group row paths; never inspect plugin data as rows."""
    paths = []

    def visit(rows, parent):
        for ident, row in rows:
            path = parent + "/" + ident if parent else ident
            paths.append(path)
            if _value(row, _key(row, "group", 2, "BASE_ROW_DUPLICATE")) != "true":
                continue
            config = _key(row, "config", 2, "BASE_ROW_DUPLICATE")
            if config is None or _value(row, config) in ("[]",):
                continue
            child = row[config + 1:_end(row, config)]
            first = next((line for line in child if _content(line)), None)
            if first is not None:
                visit(_rows(child, _indent(first), "BASE_ROW_INDENT_DRIFT"), path)
    visit(_rows(composition.splitlines(), 0, "BASE_ROW_INDENT_DRIFT"), "")
    return paths


def _key(lines, name, indent, code):
    prefix = " " * indent + name + ":"
    found = [i for i, line in enumerate(lines) if line.startswith(prefix)
             and (line == prefix or line[len(prefix)].isspace())]
    if len(found) > 1:
        _refuse(code, f"duplicate key {name}")
    return found[0] if found else None


def _value(lines, index):
    return lines[index].partition(":")[2].strip() if index is not None else None


def _base_rows(text, selector):
    lines = text.splitlines()
    matching = []
    for n, line in enumerate(lines):
        if line != "- insert:":
            continue
        section = lines[n + 1:_end(lines, n)]
        items = [i for i, item in enumerate(section) if _content(item)]
        if not items:
            continue
        for _, row in _rows(section, _indent(section[items[0]]), "BASE_ROW_INDENT_DRIFT"):
            if _value(row, _key(row, "name", 2, "BASE_ROW_DUPLICATE")) is None:
                continue
            if _scalar(_value(row, _key(row, "name", 2, "BASE_ROW_DUPLICATE")), "BASE_ROW_MISSING") != selector["name"]:
                continue
            config = _key(row, "config", 2, "BASE_ROW_DUPLICATE")
            if config is None or _value(row, config):
                continue
            fields = row[config+1:_end(row, config)]
            ident = _value(fields, _key(fields, "id", 4, "BASE_ROW_DUPLICATE"))
            if ident and _scalar(ident, "BASE_ROW_MISSING") == selector["config_id"]:
                matching.append((row, fields))
    if len(matching) != 1:
        _refuse("BASE_ROW_DUPLICATE" if matching else "BASE_ROW_MISSING", selector["config_id"])
    row, fields = matching[0]
    _enabled(row, "BASE")
    idx = _key(fields, "plugins", 4, "BASE_ROWS_NOT_LIST")
    if idx is None or _value(fields, idx):
        _refuse("BASE_ROWS_NOT_LIST", "expected config.plugins block sequence")
    content = fields[idx+1:_end(fields, idx)]
    first = next((line for line in content if _content(line)), None)
    if first is None:
        _refuse("BASE_ROWS_NOT_LIST", "empty plugin list")
    return _rows(content, _indent(first), "BASE_ROW_INDENT_DRIFT")


def _enabled(row, label):
    value = _value(row, _key(row, "disabled", 2, label + "_ROW_DUPLICATE"))
    if value not in (None, "false", "null", "~"):
        _refuse(label + "_ROW_DISABLED", "disabled or conditional merge target")


def _target(rows, name, label):
    hits = []
    for ident, row in rows:
        val = _value(row, _key(row, "name", 2, label + "_ROW_DUPLICATE"))
        if val and _scalar(val, label + "_ROW_MISSING") == name:
            hits.append((ident, row))
    if len(hits) != 1:
        _refuse(label + ("_ROW_DUPLICATE" if hits else "_ROW_MISSING"), name)
    _enabled(hits[0][1], label)
    return hits[0]


def _edit(row, field, replace, code):
    conf = _key(row, "config", 2, code)
    if conf is None:
        row.append("  config:")
        conf = len(row) - 1
    if _value(row, conf):
        _refuse(code, "config must be a block mapping")
    stop = _end(row, conf)
    idx = _key(row[conf+1:stop], field, 4, code)
    if idx is None:
        row[stop:stop] = replace(None, [])
    else:
        idx += conf + 1
        end = _end(row, idx)
        row[idx:end] = replace(_value(row, idx), row[idx+1:end])


def _skill_entries(lines):
    values = []
    for line in lines:
        if not _content(line):
            continue
        if not line.startswith("      - "):
            _refuse("SKILL_DIRS_UNSUPPORTED", "expected block sequence entries")
        scalar = line[8:].strip()
        if scalar.startswith("!!js ") and scalar[5:].strip():
            continue
        values.append(_scalar(scalar, "SKILL_DIRS_UNSUPPORTED"))
    return values


def _path_key(path):
    if os.name == "nt":
        path = path.replace("\\", "/")
    return path.rstrip("/").casefold() if sys.platform in ("win32", "darwin") else path.rstrip("/")


def validate_overlay(text, own):
    native = own["native"]
    overlay = text
    owned = _rows(overlay.splitlines(), 0, "OVERLAY_ROW_INVALID")
    overlay_cfg = own["overlay"]
    if [key for key, _ in owned] != overlay_cfg["rows"] or "!!js" in overlay:
        _refuse("OVERLAY_ROW_INVALID", "unexpected overlay rows or loader expression")
    _, overlay_persona = _target(owned, native["persona_row_name"], "OVERLAY")
    _, overlay_skill = _target(owned, native["skill_row_name"], "OVERLAY")
    tokens = own["render"]["tokens"]
    if len(overlay_persona) < 2 or len(overlay_skill) < 2 or not overlay_persona[1].startswith("  name: ") or not overlay_skill[1].startswith("  name: "):
        _refuse("OVERLAY_ROW_INVALID", "invalid row mapping")
    if overlay_persona[2:] != ["  config:", "    prefix: |", "      " + overlay_cfg["persona_body_token"]]:
        _refuse("OVERLAY_ROW_INVALID", "invalid persona overlay")
    if (len(overlay_skill) != 4 + len(native["skill_roots"])
            or overlay_skill[2:4] != ["  config:", "    customSkillDirs:"]):
        _refuse("OVERLAY_ROW_INVALID", "invalid skill overlay")
    paths = [tokens.get(token) for token in _skill_entries(overlay_skill[4:])]
    if paths != native["skill_roots"]:
        _refuse("OVERLAY_ROW_INVALID", "invalid skill roots")
    return paths


def merge(base, overlay, persona, root, own, *, source_path=None):
    native = own["native"]
    policy = own["render"]["persona_prefix"]
    body_token = native["persona_repo_token"]
    if body_token not in persona:
        _refuse("PERSONA_TOKEN_MISSING", body_token)
    body = persona.replace("\r\n", "\n").replace(body_token, root.as_posix()).strip()
    if not body or re.search(own["render"]["leftover_scan"], body):
        _refuse("PERSONA_BODY_INVALID", "empty body or unresolved tokens")
    rows = _base_rows(base, native["base_preset"]["row_selector"])
    paths = validate_overlay(overlay, own)
    persona_id, p_row = _target(rows, native["persona_row_name"], "PERSONA")
    skill_id, s_row = _target(rows, native["skill_row_name"], "SKILL")

    def prefix(val, nested):
        if any(_content(line) for line in nested):
            _refuse("PERSONA_PREFIX_UNSUPPORTED", "expected a single-line prefix")
        value = _scalar(val, "PERSONA_PREFIX_UNSUPPORTED").rstrip() if val else ""
        text = value + policy["separator"] + body if value else body
        return ["    prefix: |"] + ["      " + line if line else "" for line in text.split("\n")] + nested

    def relocate_skill_entries(nested):
        # rc.3+ resolves the bundled skills relative to its declaration's
        # module scope. Preserve that scope when the directory artifact moves.
        module_name = native["base_row_name"] + "/package.json"
        expression = ("process.getBuiltinModule('node:path').join("
                      "process.getBuiltinModule('node:path').dirname("
                      "process.getBuiltinModule('node:module').createRequire(baseUrl).resolve("
                      + repr(module_name) + ")), 'skills')")
        expected = "      - !!js " + expression
        result = []
        for line in nested:
            if line == expected:
                if source_path is None:
                    _refuse("BASE_URL_UNSUPPORTED", "declaration source is required")
                line = line.replace("createRequire(baseUrl)", "createRequire("
                                    + json.dumps(Path(source_path).absolute().as_uri()) + ")")
            result.append(line)
        return result

    def dirs(val, nested):
        if val not in (None, "", "[]"):
            _refuse("SKILL_DIRS_UNSUPPORTED", "expected customSkillDirs block sequence")
        current = {_path_key(item) for item in _skill_entries(nested)}
        output = ["    customSkillDirs:", *relocate_skill_entries(nested)]
        for path in paths:
            value = (root / path).as_posix()
            if _path_key(value) not in current:
                output.append("      - " + json.dumps(value, ensure_ascii=False))
        return output

    _edit(p_row, "prefix", prefix, "PERSONA_PREFIX_UNSUPPORTED")
    _edit(s_row, "customSkillDirs", dirs, "SKILL_DIRS_UNSUPPORTED")
    result = "\n".join(line for _, row in rows for line in row).rstrip("\n") + "\n"
    lines = result.splitlines()
    for i, line in enumerate(lines):
        if not _content(line) or not re.search(r"(?:^|[: -])!!js(?:\s|$)", line):
            continue
        expression = "\n".join(lines[i:_end(lines, i)])
        if re.search(r"\bbaseUrl\b", expression):
            _refuse("BASE_URL_UNSUPPORTED", "an inherited expression still depends on the preset location")
    if re.search(own["render"]["leftover_scan"], result):
        _refuse("RENDER_TOKEN_LEFTOVER", "unresolved token in derived preset")
    return result, [persona_id, skill_id]


def _base_source(plane, raw_path, asar_module):
    if plane["kind"] == "asar-desktop":
        reader = asar_module.AsarReader(plane["anchor"])
        if reader.identity()["header_sha256"] != plane["header_sha256"]:
            _refuse("PLANE_UNUSABLE", "desktop archive changed during rendering")
        try:
            return reader.read_bytes(raw_path), Path(plane["anchor"]) / raw_path
        except asar_module.AsarError as exc:
            _refuse("BASE_PRESET_UNREADABLE", str(exc))
    suffix = raw_path.split("/node_modules/", 1)[1]
    anchor = Path(plane["resolution_anchor"]).parent
    for folder in [anchor / "node_modules", Path(plane["node_modules"])]:
        candidate = folder / suffix
        if candidate.is_file():
            return candidate.read_bytes(), candidate
    _refuse("BASE_PRESET_MISSING", f"{suffix} under {anchor}")


def derive_preset(root, *, plane=None, env=None):
    root = Path(root).resolve()
    infra = str(root / "skills/software-project-governance/infra")
    if infra not in sys.path:
        sys.path.insert(0, infra)
    import dsh_asar
    import dsh_plane
    contract = json.loads((root / "adapters/dsh/host-contract.json").read_bytes())
    own = contract["own"]
    if plane is None:
        planes = dsh_plane.resolve(os.environ if env is None else env)
        if not planes:
            _refuse("HOST_PLANE_ABSENT", "no installed DSH plane was discovered")
        plane = planes[0]
    if hasattr(plane, "identity"):
        plane = plane.identity()
    if not plane or not plane.get("usable") or not plane.get("resolution_anchor"):
        _refuse("PLANE_UNUSABLE", (plane or {}).get("detail", "no usable host plane"))
    preset = own["native"]["base_preset_id_default"]
    raw_path = own["native"]["base_preset"]["patch_rel"].format(id=preset)
    try:
        base, source_path = _base_source(plane, raw_path, dsh_asar)
        overlay = (root / own["overlay"]["path"]).read_bytes()
        persona = (root / own["native"]["persona_source"]).read_bytes()
        text, overlay_ids = merge(base.decode(), overlay.decode(), persona.decode(), root, own, source_path=source_path)
    except (OSError, UnicodeError, dsh_asar.AsarError) as exc:
        _refuse("BASE_PRESET_UNREADABLE", str(exc))
    ids = row_ids(text)
    version = json.loads((root / "package.json").read_bytes())["version"]
    overlay_hash = sha256(overlay).hexdigest()
    text = (f"# Generated governance preset {version}\n"
            f"# Host {plane['kind']} {plane['dsh_version']} / preset {preset}\n"
            f"# Overlay SHA-256 {overlay_hash}\n"
            "# Regenerate with adapters/dsh/launch.py --install\n" + text)
    provenance = {
        "schema": own["preset"]["render_provenance"]["schema"], "package_version": version,
        "rendered_at": datetime.now(timezone.utc).isoformat(),
        "overlay": {"path": own["overlay"]["path"], "sha256": overlay_hash},
        "persona": {"path": own["native"]["persona_source"], "sha256": sha256(persona).hexdigest()},
        "plane": {key: plane.get(key) for key in ("kind", "dsh_version", "anchor", "header_sha256")},
        "base": {"preset": preset, "source_path": source_path.as_posix(), "source_sha256": sha256(base).hexdigest(), "row_count": len(ids), "row_ids": ids},
        "overlay_rows": overlay_ids,
        "rows": [{"id": key, "origin": "overlay" if key in overlay_ids else "base"} for key in ids],
        "policy": {"newline": own["render"]["newline_policy"], "write_policy": own["preset"]["write_policy"]},
        "composition_sha256": sha256(text.encode()).hexdigest(), "row_ids": ids,
    }
    return {"composition": text, "provenance": provenance}
