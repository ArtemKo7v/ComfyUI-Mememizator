import copy
from pathlib import Path
from typing import Any

from .config import get_first_template_name, get_template_config, get_template_names
from .constants import TEMPLATE_DEFAULT_FONT, TEXT_POSITION_OPTIONS
from .fonts import get_font_candidates, get_settings_font_options
from .utils import get_int, normalize_optional_string


# Returns the first configured font name for a template.
def get_primary_font_name(template: dict[str, Any]) -> str:
    for key in ("font", "title", "subtitle"):
        candidates = get_font_candidates(template.get(key, {}))
        if candidates:
            return Path(candidates[0]).name
    return TEMPLATE_DEFAULT_FONT


# Returns a valid text position for a template.
def get_text_position_value(template: dict[str, Any]) -> str:
    text_area = template.get("text_area", {})
    value = normalize_optional_string(text_area.get("position"))
    if value in TEXT_POSITION_OPTIONS:
        return value
    return "below"


# Builds default settings values from a template.
def get_settings_defaults(template_name: str | None = None) -> dict[str, Any]:
    template = get_template_config(template_name or get_first_template_name())
    image_offset = template.get("image_offset", {})
    frame = template.get("frame", {})
    text_area = template.get("text_area", {})
    canvas_extra = template.get("canvas_extra", {})
    text_outline = template.get("text_outline", {})
    title = template.get("title", {})
    subtitle = template.get("subtitle", {})

    return {
        "template_name": template.get("name", get_first_template_name()),
        "background": str(template.get("background_color", "")),
        "text": str(template.get("text_color", "")),
        "padding_x": get_int(image_offset, "x", -1, minimum=-1),
        "padding_y": get_int(image_offset, "y", -1, minimum=-1),
        "frame_color": str(frame.get("color", "")),
        "frame_gap": get_int(frame, "gap", -1, minimum=-1),
        "frame_thickness": get_int(frame, "thickness", -1, minimum=-1),
        "text_padding_x": get_int(text_area, "padding_x", -1, minimum=-1),
        "text_padding_bottom": get_int(text_area, "padding_bottom", -1, minimum=-1),
        "text_position": get_text_position_value(template),
        "outline_color": str(text_outline.get("color", "#000000")),
        "outline_thickness": get_int(text_outline, "thickness", -1, minimum=-1),
        "gap_from_image": get_int(text_area, "gap_from_image", -1, minimum=-1),
        "block_spacing": get_int(text_area, "block_spacing", -1, minimum=-1),
        "multiline_spacing": get_int(text_area, "multiline_spacing", -1, minimum=-1),
        "extra_width": get_int(canvas_extra, "width", -1, minimum=-1),
        "extra_height": get_int(canvas_extra, "height", -1, minimum=-1),
        "title_size": get_int(title, "size", -1, minimum=-1),
        "title_min_size": get_int(title, "min_size", -1, minimum=-1),
        "subtitle_size": get_int(subtitle, "size", -1, minimum=-1),
        "subtitle_min_size": get_int(subtitle, "min_size", -1, minimum=-1),
        "font_name": get_primary_font_name(template),
    }


# Applies a non-negative integer override.
def apply_int_override(target: dict[str, Any], key: str, value: Any) -> None:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and int(value) >= 0:
        target[key] = int(value)


# Applies a non-empty string override.
def apply_string_override(target: dict[str, Any], key: str, value: Any) -> None:
    normalized = normalize_optional_string(value)
    if normalized is not None:
        target[key] = normalized


# Applies settings-node overrides to a template config.
def apply_settings_override(template: dict[str, Any], settings: Any) -> dict[str, Any]:
    result = copy.deepcopy(template)
    if not isinstance(settings, dict):
        return result

    apply_string_override(result, "background_color", settings.get("background"))
    apply_string_override(result, "text_color", settings.get("text"))

    image_offset = result.setdefault("image_offset", {})
    frame = result.setdefault("frame", {})
    text_area = result.setdefault("text_area", {})
    canvas_extra = result.setdefault("canvas_extra", {})
    text_outline = result.setdefault("text_outline", {})
    title = result.setdefault("title", {})
    subtitle = result.setdefault("subtitle", {})
    font = result.setdefault("font", {})

    apply_int_override(image_offset, "x", settings.get("padding_x"))
    apply_int_override(image_offset, "y", settings.get("padding_y"))
    apply_string_override(frame, "color", settings.get("frame_color"))
    apply_int_override(frame, "gap", settings.get("frame_gap"))
    apply_int_override(frame, "thickness", settings.get("frame_thickness"))
    apply_int_override(text_area, "padding_x", settings.get("text_padding_x"))
    apply_int_override(text_area, "padding_bottom", settings.get("text_padding_bottom"))
    text_position = normalize_optional_string(settings.get("text_position"))
    if text_position in TEXT_POSITION_OPTIONS:
        text_area["position"] = text_position
    apply_string_override(text_outline, "color", settings.get("outline_color"))
    apply_int_override(text_outline, "thickness", settings.get("outline_thickness"))
    apply_int_override(text_area, "gap_from_image", settings.get("gap_from_image"))
    apply_int_override(text_area, "block_spacing", settings.get("block_spacing"))
    apply_int_override(text_area, "multiline_spacing", settings.get("multiline_spacing"))
    apply_int_override(canvas_extra, "width", settings.get("extra_width"))
    apply_int_override(canvas_extra, "height", settings.get("extra_height"))
    apply_int_override(title, "size", settings.get("title_size"))
    apply_int_override(title, "min_size", settings.get("title_min_size"))
    apply_int_override(subtitle, "size", settings.get("subtitle_size"))
    apply_int_override(subtitle, "min_size", settings.get("subtitle_min_size"))

    font_name = normalize_optional_string(settings.get("font_name"))
    if font_name and font_name != TEMPLATE_DEFAULT_FONT:
        font["font_candidates"] = [font_name]
        font["download"] = {}

    return result


