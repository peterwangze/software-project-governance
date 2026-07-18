"""Dependency-free fail-closed validator for the release manifest schema."""

from datetime import datetime
import json
import re
from typing import Any, Dict, List


RFC3339_RE = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"
    r"(?:\.[0-9]+)?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])\Z"
)


def _resolve_ref(root_schema: Dict[str, Any], ref: str) -> Dict[str, Any]:
    if not ref.startswith("#/"):
        raise ValueError(f"unsupported schema reference `{ref}`")
    current: Any = root_schema
    for part in ref[2:].split("/"):
        current = current[part.replace("~1", "/").replace("~0", "~")]
    if not isinstance(current, dict):
        raise ValueError(f"schema reference `{ref}` does not resolve to an object")
    return current


def _matches_type(value: Any, expected: str) -> bool:
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }.get(expected, False)


def validate_schema(instance: Any, schema: Dict[str, Any]) -> List[str]:
    issues: List[str] = []

    def walk(value: Any, rule: Dict[str, Any], path: str) -> List[str]:
        local: List[str] = []
        if "$ref" in rule:
            return walk(value, _resolve_ref(schema, rule["$ref"]), path)
        if "oneOf" in rule:
            matches = [candidate for candidate in rule["oneOf"] if not walk(value, candidate, path)]
            if len(matches) != 1:
                local.append(f"{path}: must match exactly one schema branch")
            return local
        if "allOf" in rule:
            for candidate in rule["allOf"]:
                local.extend(walk(value, candidate, path))
        if "if" in rule:
            condition_matches = not walk(value, rule["if"], path)
            branch = rule.get("then") if condition_matches else rule.get("else")
            if isinstance(branch, dict):
                local.extend(walk(value, branch, path))
        expected = rule.get("type")
        if expected is not None:
            types = expected if isinstance(expected, list) else [expected]
            if not any(_matches_type(value, item) for item in types):
                return [f"{path}: expected type {types}"]
        if "const" in rule and value != rule["const"]:
            local.append(f"{path}: expected constant {rule['const']!r}")
        if "enum" in rule and value not in rule["enum"]:
            local.append(f"{path}: value is not in enum")
        if isinstance(value, str):
            if len(value) < int(rule.get("minLength", 0)):
                local.append(f"{path}: string is shorter than minLength")
            pattern = rule.get("pattern")
            if pattern is not None:
                try:
                    if re.search(pattern, value) is None:
                        local.append(f"{path}: string does not match pattern")
                except re.error as exc:
                    raise ValueError(f"invalid schema regex at {path}: {exc}") from exc
            if rule.get("format") == "date-time":
                try:
                    if RFC3339_RE.fullmatch(value) is None:
                        raise ValueError("not RFC3339")
                    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    if parsed.tzinfo is None:
                        raise ValueError("timezone required")
                except ValueError:
                    local.append(f"{path}: invalid date-time")
        if isinstance(value, list):
            if len(value) < int(rule.get("minItems", 0)):
                local.append(f"{path}: array is shorter than minItems")
            if rule.get("uniqueItems") is True:
                identities = [
                    json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                    for item in value
                ]
                if len(identities) != len(set(identities)):
                    local.append(f"{path}: array items must be unique")
            item_rule = rule.get("items")
            if isinstance(item_rule, dict):
                for index, item in enumerate(value):
                    local.extend(walk(item, item_rule, f"{path}[{index}]"))
        if isinstance(value, dict):
            for required in rule.get("required", []):
                if required not in value:
                    local.append(f"{path}: missing required property `{required}`")
            properties = rule.get("properties", {})
            for key, item in value.items():
                if key in properties:
                    local.extend(walk(item, properties[key], f"{path}.{key}"))
                elif rule.get("additionalProperties") is False:
                    local.append(f"{path}: additional property `{key}` is forbidden")
        return local

    issues.extend(walk(instance, schema, "$"))
    return issues
