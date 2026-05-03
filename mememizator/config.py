import copy
import json
import shutil
from typing import Any

from .constants import (
    CONFIG_DIR,
    CONFIG_PATH,
    DEFAULT_CONFIG,
    LEGACY_DEMOTIVATOR_FONT_CANDIDATES,
    PACKAGE_CONFIG_PATH,
)
from .utils import deep_copy_config, deep_merge_dicts, log, read_json, write_json


# Loads the packaged default config or the built-in fallback.
def load_packaged_default_config() -> dict[str, Any]:
    if PACKAGE_CONFIG_PATH.exists():
        try:
            return read_json(PACKAGE_CONFIG_PATH)
        except (OSError, json.JSONDecodeError) as exc:
            log(f"Failed to read packaged config {PACKAGE_CONFIG_PATH}: {exc}")

    return deep_copy_config(DEFAULT_CONFIG)


# Removes obsolete fields from legacy templates.
def upgrade_legacy_template(template: dict[str, Any]) -> dict[str, Any]:
    upgraded = copy.deepcopy(template)
    if upgraded.get("name") != "Classic Demotivator":
        return upgraded

    for section_name in ("title", "subtitle"):
        section = upgraded.get(section_name)
        if not isinstance(section, dict):
            continue

        candidates = section.get("font_candidates")
        if candidates == LEGACY_DEMOTIVATOR_FONT_CANDIDATES:
            section.pop("font_candidates", None)

    return upgraded


# Validates and merges a config with default template values.
def normalize_config(config: Any) -> dict[str, Any]:
    default_config = load_packaged_default_config()
    normalized = deep_copy_config(default_config)
    default_templates = {
        template["name"]: template
        for template in default_config.get("templates", [])
        if isinstance(template, dict) and isinstance(template.get("name"), str)
    }

    if not isinstance(config, dict):
        return normalized

    templates = config.get("templates")
    if not isinstance(templates, list):
        return normalized

    valid_templates: list[dict[str, Any]] = []
    for template in templates:
        if not isinstance(template, dict):
            continue

        name = template.get("name")
        template_type = template.get("type")
        if not isinstance(name, str) or not name.strip():
            continue
        if not isinstance(template_type, str) or not template_type.strip():
            continue

        default_template = default_templates.get(name)
        if isinstance(default_template, dict):
            merged_template = deep_merge_dicts(default_template, template)
        else:
            merged_template = copy.deepcopy(template)

        valid_templates.append(upgrade_legacy_template(merged_template))

    if valid_templates:
        existing_names = {template["name"] for template in valid_templates}
        for default_template in default_config.get("templates", []):
            if not isinstance(default_template, dict):
                continue
            name = default_template.get("name")
            if isinstance(name, str) and name not in existing_names:
                valid_templates.append(copy.deepcopy(default_template))
        normalized["templates"] = valid_templates

    return normalized


# Loads the user config and writes normalized defaults when needed.
def load_config() -> dict[str, Any]:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    default_config = normalize_config(load_packaged_default_config())
    if not CONFIG_PATH.exists():
        if PACKAGE_CONFIG_PATH.exists():
            shutil.copyfile(PACKAGE_CONFIG_PATH, CONFIG_PATH)
        else:
            write_json(CONFIG_PATH, default_config)
        log(f"Created config file at {CONFIG_PATH}")
        return default_config

    try:
        config = read_json(CONFIG_PATH)
    except (OSError, json.JSONDecodeError) as exc:
        log(f"Failed to read config from {CONFIG_PATH}: {exc}")
        write_json(CONFIG_PATH, default_config)
        log(f"Reset config file at {CONFIG_PATH}")
        return default_config

    normalized = normalize_config(config)
    if normalized != config:
        write_json(CONFIG_PATH, normalized)
        log(f"Normalized config file at {CONFIG_PATH}")

    return normalized


# Returns all configured template names.
def get_template_names() -> tuple[str, ...]:
    templates = load_config().get("templates", [])
    names = [
        template["name"]
        for template in templates
        if isinstance(template, dict) and isinstance(template.get("name"), str)
    ]
    return tuple(names) or ("Classic Demotivator",)


# Returns the config for a named template or the first template.
def get_template_config(template_name: str) -> dict[str, Any]:
    config = load_config()
    templates = config.get("templates", [])

    fallback_template = None
    for template in templates:
        if not isinstance(template, dict):
            continue
        if fallback_template is None:
            fallback_template = template
        if template.get("name") == template_name:
            return template

    if fallback_template is not None:
        return fallback_template

    raise RuntimeError("No meme templates found in config.json")


# Returns the first available template name.
def get_first_template_name() -> str:
    names = get_template_names()
    return names[0]


