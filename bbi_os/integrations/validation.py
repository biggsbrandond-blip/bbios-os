from typing import Any, Dict, Type


TYPE_MAP = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "object": dict,
    "array": list,
}


def validate_schema(
    value: Any, schema: Dict[str, Any], error_type: Type[Exception], label: str
) -> None:
    expected_name = schema.get("type")
    expected = TYPE_MAP.get(expected_name)
    if expected and not isinstance(value, expected):
        raise error_type(f"{label} must be {expected_name}")
    if isinstance(value, dict):
        missing = [name for name in schema.get("required", []) if name not in value]
        if missing:
            raise error_type(f"{label} missing field(s): {', '.join(sorted(missing))}")
        for name, rules in schema.get("properties", {}).items():
            if name in value:
                validate_schema(value[name], rules, error_type, f"{label}.{name}")

