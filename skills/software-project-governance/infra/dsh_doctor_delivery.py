"""Read-only comparison of the installed DSH directory preset and its recorded origins."""

from hashlib import sha256
import json
import re


def _row_difference(actual, expected):
    extra = [name for name in actual if name not in expected]
    missing = [name for name in expected if name not in actual]
    findings = []
    if extra:
        findings.append(("RESIDUAL_ROWS", ", ".join(extra)))
    if missing:
        findings.append(("MISSING_ROWS", ", ".join(missing)))
    if actual != expected and not findings:
        findings.append(("ROW_ORDER_CHANGED", "installed row order differs"))
    return findings


def _load_provenance(path, spec):
    document = json.loads(path.read_bytes())
    if not isinstance(document, dict) or document.get("schema") != spec["schema"]:
        raise ValueError("unrecognized render provenance schema")
    required = set(spec["fields"]) - document.keys()
    if required:
        raise ValueError(f"missing provenance fields: {sorted(required)}")
    rows = document["rows"]
    if not isinstance(rows, list) or not rows or any(
        not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]
        for row in rows
    ):
        raise ValueError("provenance row list is invalid")
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("provenance row IDs are not unique")
    if not isinstance(document["plane"], dict) or not document["plane"].get("kind"):
        raise ValueError("provenance does not identify the recorded plane")
    if not re.fullmatch(r"[0-9a-f]{64}", str(document.get("composition_sha256", ""))):
        raise ValueError("provenance has no valid composition SHA-256")
    return document


def inspect_composition(ctx, composition, sidecar, spec, package_version, payload_names):
    """Offline uses only installed files. Online also compares to the selected host."""
    import dsh_compat

    renderer = dsh_compat._load_preset_renderer()
    face = {"composition": str(composition), "provenance": str(sidecar)}
    findings = []
    try:
        raw = composition.read_bytes()
        text = raw.decode("utf-8")
        rows = renderer.row_ids(text)
        row_paths = renderer.row_paths(text)
        if not rows:
            raise ValueError("no top-level rows")
    except (OSError, ValueError) as error:
        return face, [("COMPOSITION_INVALID", str(error))]
    digest = sha256(raw).hexdigest()
    face.update(row_ids=rows, row_paths=row_paths, composition_sha256=digest)
    recorded = None
    if not sidecar.exists():
        findings.append(("PROVENANCE_ABSENT", "previous installation has no render provenance"))
    else:
        try:
            recorded = _load_provenance(sidecar, spec)
        except (ValueError, OSError) as error:
            return face, [("PROVENANCE_INVALID", str(error))]
        expected = [row["id"] for row in recorded["rows"]]
        face["recorded_plane"] = recorded["plane"]
        try:
            renderer.verify_payload(composition.parent, spec, payload_names)
        except (ValueError, OSError) as error:
            findings.append(("PAYLOAD_DRIFT", str(error)))
        findings.extend(_row_difference(rows, expected))
        if recorded["package_version"] != package_version:
            findings.append(("VERSION_MISMATCH", "provenance package version differs from this package"))
        if recorded["composition_sha256"] != digest:
            findings.append(("CONTENT_EDITED", "installed bytes differ from the saved render digest"))

    if not ctx.offline:
        try:
            derived = renderer.derive_preset(ctx.root, env=ctx.env)
            current = derived["provenance"]
            expected_paths = renderer.row_paths(derived["composition"])
        except (OSError, ValueError) as error:
            findings.append(("PLANE_UNAVAILABLE", str(error)))
        else:
            face["current_plane"] = current["plane"]
            face["expected_row_paths"] = expected_paths
            for finding in _row_difference(row_paths, expected_paths):
                if finding not in findings:
                    findings.append(finding)
            if recorded and recorded["plane"] != current["plane"]:
                findings.append(("PLANE_VERSION_DRIFT", "current plane differs from the recorded installation"))
            if recorded and digest != current["composition_sha256"] and digest == recorded["composition_sha256"]:
                findings.append(("RENDER_DRIFT", "matching version marker and saved digest, but current render differs"))
    return face, findings
