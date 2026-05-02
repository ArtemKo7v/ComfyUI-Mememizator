import copy
import json
from pathlib import Path
from typing import Any


# Writes a message with the node log prefix.
def log(message: str) -> None:
    print(f"[ComfyUI-Mememizator]: {message}")


# Reads JSON from disk using UTF-8 with BOM support.
def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


# Writes pretty JSON to disk.
def write_json(path: Path, data: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


# Returns a deep copy of config data.
def deep_copy_config(data: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(data)


# Recursively merges override values into a base dictionary.
def deep_merge_dicts(base: Any, override: Any) -> Any:
    if not isinstance(base, dict) or not isinstance(override, dict):
        return copy.deepcopy(override)

    merged = copy.deepcopy(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge_dicts(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)

    return merged


# Reads an integer value with bounds and fallback handling.
def get_int(data: dict[str, Any], key: str, default: int, minimum: int = 0) -> int:
    value = data.get(key, default)
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return max(minimum, int(value))
    return default


# Normalizes text input for rendering.
def normalize_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines).strip()


# Normalizes an optional string value.
def normalize_optional_string(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None

