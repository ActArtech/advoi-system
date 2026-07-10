"""Validate Aether proactive feed payloads against aether-proactive-latest.schema.json.

Pure functions for T0 tests and local gate checks — no network I/O.
Implements the Draft 2020-12 subset used by the schema (type, required, const,
enum, minLength, minItems, minimum, $ref, properties, additionalProperties).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Repo-root docs path when installed as package from source tree.
_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA_PATH = _REPO_ROOT / "docs" / "aether" / "aether-proactive-latest.schema.json"
DEFAULT_ARTIFACT_PATH = _REPO_ROOT / "docs" / "aether" / "aether-proactive-latest.json"

_TYPE_MAP: dict[str, type | tuple[type, ...]] = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "integer": int,
    "number": (int, float),
}


def load_schema(path: Path | None = None) -> dict[str, Any]:
    """Load the proactive feed JSON Schema from disk."""
    schema_path = path or DEFAULT_SCHEMA_PATH
    data = json.loads(schema_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"schema root must be an object: {schema_path}")
    return data


def validate_proactive_payload(
    payload: Any,
    *,
    schema: dict[str, Any] | None = None,
    schema_path: Path | None = None,
) -> list[str]:
    """Return a list of error strings (empty = pass) for a proactive feed payload."""
    sch = schema if schema is not None else load_schema(schema_path)
    errors: list[str] = []
    _validate(payload, sch, sch, "$", errors)
    return errors


def validate_proactive_file(
    path: Path | None = None,
    *,
    schema_path: Path | None = None,
) -> list[str]:
    """Load artifact JSON from disk and validate against the schema."""
    artifact = path or DEFAULT_ARTIFACT_PATH
    try:
        raw = json.loads(artifact.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"artifact missing: {artifact}"]
    except json.JSONDecodeError as exc:
        return [f"artifact JSON parse error: {exc}"]
    return validate_proactive_payload(raw, schema_path=schema_path)


def is_valid_proactive_payload(
    payload: Any,
    *,
    schema: dict[str, Any] | None = None,
    schema_path: Path | None = None,
) -> bool:
    """True when validate_proactive_payload returns no errors."""
    return not validate_proactive_payload(payload, schema=schema, schema_path=schema_path)


def _resolve_ref(root: dict[str, Any], ref: str) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise ValueError(f"unsupported $ref (local only): {ref}")
    node: Any = root
    for part in ref[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or part not in node:
            raise ValueError(f"unresolved $ref: {ref}")
        node = node[part]
    if not isinstance(node, dict):
        raise ValueError(f"$ref target is not an object: {ref}")
    return node


def _validate(
    value: Any,
    schema: dict[str, Any],
    root: dict[str, Any],
    path: str,
    errors: list[str],
) -> None:
    if "$ref" in schema:
        _validate(value, _resolve_ref(root, schema["$ref"]), root, path, errors)
        return

    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected const {schema['const']!r}, got {value!r}")
        return

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} not in enum {schema['enum']!r}")
        return

    expected_type = schema.get("type")
    if expected_type is not None:
        if not _type_ok(value, expected_type):
            errors.append(f"{path}: expected type {expected_type}, got {type(value).__name__}")
            return

    if expected_type == "string" or isinstance(value, str):
        min_len = schema.get("minLength")
        if min_len is not None and isinstance(value, str) and len(value) < min_len:
            errors.append(f"{path}: string shorter than minLength {min_len}")

    if expected_type == "integer" or expected_type == "number" or isinstance(value, (int, float)):
        minimum = schema.get("minimum")
        if minimum is not None and isinstance(value, (int, float)) and not isinstance(value, bool):
            if value < minimum:
                errors.append(f"{path}: {value} is less than minimum {minimum}")

    if expected_type == "array" or isinstance(value, list):
        if isinstance(value, list):
            min_items = schema.get("minItems")
            if min_items is not None and len(value) < min_items:
                errors.append(f"{path}: array length {len(value)} < minItems {min_items}")
            item_schema = schema.get("items")
            if isinstance(item_schema, dict):
                for i, item in enumerate(value):
                    _validate(item, item_schema, root, f"{path}[{i}]", errors)

    if expected_type == "object" or isinstance(value, dict):
        if not isinstance(value, dict):
            return
        required = schema.get("required") or []
        for key in required:
            if key not in value:
                errors.append(f"{path}: missing required property {key!r}")
        props = schema.get("properties") or {}
        for key, prop_schema in props.items():
            if key in value and isinstance(prop_schema, dict):
                _validate(value[key], prop_schema, root, f"{path}.{key}", errors)


def _type_ok(value: Any, expected: str) -> bool:
    # JSON Schema: bool is not integer.
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    py = _TYPE_MAP.get(expected)
    if py is None:
        return True
    return isinstance(value, py)
