import copy
import json
import os
import shutil
import urllib.request
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

try:
    from aiohttp import web
    from server import PromptServer
except ImportError:
    PromptServer = None
    web = None
try:
    from aiohttp import web
    from server import PromptServer
except ImportError:
    PromptServer = None
    web = None


BASE_DIR = Path(__file__).resolve().parent
USER_DIR = Path(os.getcwd()) / "user" / "default"
CONFIG_DIR = USER_DIR / "ComfyUI-Mememizator"
CONFIG_PATH = CONFIG_DIR / "config.json"
FONTS_DIR = CONFIG_DIR / "fonts"
PACKAGE_CONFIG_PATH = BASE_DIR / "config.json"
SETTINGS_TYPE = "MEMEMIZATOR_SETTINGS"
TEMPLATE_DEFAULT_FONT = "(template default)"
TEXT_POSITION_OPTIONS = ("below", "above", "overlay")
LEGACY_DEMOTIVATOR_FONT_CANDIDATES = [
    "times.ttf",
    "Times New Roman.ttf",
    "times new roman.ttf",
    "DejaVuSerif.ttf",
    "LiberationSerif-Regular.ttf",
    "NotoSerif-Regular.ttf",
]
DEFAULT_CONFIG: dict[str, Any] = {
    "templates": [
        {
            "name": "Classic Demotivator",
            "type": "classic_demotivator",
            "background_color": "#000000",
            "text_color": "#FFFFFF",
            "canvas_extra": {
                "width": 40,
                "height": 140,
            },
            "image_offset": {
                "x": 20,
                "y": 20,
            },
            "frame": {
                "color": "#FFFFFF",
                "gap": 4,
                "thickness": 2,
            },
            "text_area": {
                "padding_x": 20,
                "padding_bottom": 16,
                "gap_from_image": 20,
                "block_spacing": 8,
                "multiline_spacing": 4,
                "position": "below",
            },
            "text_outline": {
                "color": "#000000",
                "thickness": 0,
            },
            "font": {
                "font_candidates": [
                    "TR Impact.ttf",
                ],
                "download": {
                    "url": "https://font.download/dl/font/tr-impact.zip",
                    "target_file": "TR Impact.ttf",
                    "archive_member": "TR Impact.ttf",
                },
            },
            "title": {
                "size": 128,
                "min_size": 64,
            },
            "subtitle": {
                "size": 64,
                "min_size": 32,
            },
        }
    ]
}
ATTEMPTED_FONT_DOWNLOADS: set[str] = set()


def log(message: str) -> None:
    print(f"[ComfyUI-Mememizator]: {message}")


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def write_json(path: Path, data: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def require_pillow():
    try:
        from PIL import Image, ImageColor, ImageDraw, ImageFont
    except ImportError as exc:
        raise RuntimeError(
            "Pillow is required for ComfyUI-Mememizator. Install the custom node dependencies first."
        ) from exc

    return Image, ImageColor, ImageDraw, ImageFont


def require_numpy():
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError(
            "NumPy is required for ComfyUI-Mememizator. Install the custom node dependencies first."
        ) from exc

    return np


def require_torch():
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError(
            "PyTorch is required for ComfyUI-Mememizator. This node must run inside a ComfyUI environment."
        ) from exc

    return torch


def deep_copy_config(data: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(data)


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


def load_packaged_default_config() -> dict[str, Any]:
    if PACKAGE_CONFIG_PATH.exists():
        try:
            return read_json(PACKAGE_CONFIG_PATH)
        except (OSError, json.JSONDecodeError) as exc:
            log(f"Failed to read packaged config {PACKAGE_CONFIG_PATH}: {exc}")

    return deep_copy_config(DEFAULT_CONFIG)


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
        normalized["templates"] = valid_templates

    return normalized


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


CONFIG = load_config()

if PromptServer is not None and web is not None:
    routes = PromptServer.instance.routes

    @routes.get("/artemko7v/mememizator/config")
    async def mememizator_config_route(request):
        return web.json_response(load_config())

def get_template_names() -> tuple[str, ...]:
    templates = load_config().get("templates", [])
    names = [
        template["name"]
        for template in templates
        if isinstance(template, dict) and isinstance(template.get("name"), str)
    ]
    return tuple(names) or ("Classic Demotivator",)


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


def get_first_template_name() -> str:
    names = get_template_names()
    return names[0]


def get_primary_font_name(template: dict[str, Any]) -> str:
    for key in ("font", "title", "subtitle"):
        candidates = get_font_candidates(template.get(key, {}))
        if candidates:
            return Path(candidates[0]).name
    return TEMPLATE_DEFAULT_FONT


def get_text_position_value(template: dict[str, Any]) -> str:
    text_area = template.get("text_area", {})
    value = normalize_optional_string(text_area.get("position"))
    if value in TEXT_POSITION_OPTIONS:
        return value
    return "below"


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


def get_int(data: dict[str, Any], key: str, default: int, minimum: int = 0) -> int:
    value = data.get(key, default)
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return max(minimum, int(value))
    return default


def get_color(value: Any, fallback: str = "#FFFFFF") -> tuple[int, int, int]:
    _, ImageColor, _, _ = require_pillow()

    if isinstance(value, str):
        try:
            return ImageColor.getrgb(value)
        except ValueError:
            pass

    return ImageColor.getrgb(fallback)


def normalize_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def normalize_optional_string(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None

def get_font_candidates(font_config: Any) -> list[str]:
    if not isinstance(font_config, dict):
        return []

    candidates = font_config.get("font_candidates", [])
    if isinstance(candidates, str):
        return [candidates]
    if isinstance(candidates, list):
        return [candidate for candidate in candidates if isinstance(candidate, str) and candidate.strip()]
    return []


def extract_download_config(font_config: Any) -> dict[str, Any]:
    if not isinstance(font_config, dict):
        return {}

    download = font_config.get("download", {})
    return download if isinstance(download, dict) else {}


def iter_font_candidates(candidates: list[str] | tuple[str, ...] | str | Any) -> list[Path]:
    if isinstance(candidates, str):
        candidates = [candidates]
    elif not isinstance(candidates, (list, tuple)):
        candidates = []

    common_dirs = [
        BASE_DIR,
        CONFIG_DIR,
        FONTS_DIR,
        Path.cwd(),
        Path("C:/Windows/Fonts"),
        Path("/usr/share/fonts"),
        Path("/usr/local/share/fonts"),
        Path.home() / ".fonts",
        Path("/Library/Fonts"),
        Path("/System/Library/Fonts"),
    ]

    resolved: list[Path] = []
    seen: set[str] = set()

    for candidate in candidates:
        if not isinstance(candidate, str) or not candidate.strip():
            continue

        raw_path = Path(candidate)
        possible_paths = [raw_path]
        possible_paths.extend(directory / candidate for directory in common_dirs)

        for path in possible_paths:
            try:
                normalized = str(path.resolve(strict=False)).lower()
            except OSError:
                normalized = str(path).lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            if path.is_file():
                resolved.append(path)

    return resolved


def extract_font_from_zip(zip_bytes: bytes, destination_dir: Path, target_file: str, archive_member: str | None = None) -> bool:
    destination_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
        font_members = [
            member
            for member in archive.namelist()
            if not member.endswith("/") and Path(member).suffix.lower() in {".ttf", ".otf"}
        ]
        if not font_members:
            return False

        selected_member = None
        if isinstance(archive_member, str) and archive_member.strip():
            wanted_name = Path(archive_member).name.lower()
            for member in font_members:
                if Path(member).name.lower() == wanted_name:
                    selected_member = member
                    break

        if selected_member is None:
            target_name = Path(target_file).name.lower()
            for member in font_members:
                if Path(member).name.lower() == target_name:
                    selected_member = member
                    break

        if selected_member is None:
            selected_member = font_members[0]

        extracted_bytes = archive.read(selected_member)
        output_path = destination_dir / target_file
        output_path.write_bytes(extracted_bytes)
        return output_path.is_file()


def download_font_assets(font_config: Any) -> None:
    candidates = get_font_candidates(font_config)
    if iter_font_candidates(candidates):
        return

    download_config = extract_download_config(font_config)
    download_url = download_config.get("url")
    target_file = download_config.get("target_file")
    archive_member = download_config.get("archive_member")

    if not isinstance(download_url, str) or not download_url.strip():
        return
    if not isinstance(target_file, str) or not target_file.strip():
        if candidates:
            target_file = Path(candidates[0]).name
        else:
            return

    attempt_key = f"{download_url}|{target_file}"
    if attempt_key in ATTEMPTED_FONT_DOWNLOADS:
        return
    ATTEMPTED_FONT_DOWNLOADS.add(attempt_key)

    FONTS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        request = urllib.request.Request(
            download_url,
            headers={"User-Agent": "ComfyUI-Mememizator/0.0.1"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read()
    except Exception as exc:
        log(f"Failed to download font from {download_url}: {exc}")
        return

    try:
        if download_url.lower().endswith(".zip"):
            if extract_font_from_zip(payload, FONTS_DIR, target_file, archive_member if isinstance(archive_member, str) else None):
                log(f"Downloaded font {target_file} to {FONTS_DIR}")
            else:
                log(f"Downloaded archive from {download_url}, but no font file was found inside")
            return

        output_path = FONTS_DIR / target_file
        output_path.write_bytes(payload)
        log(f"Downloaded font {target_file} to {FONTS_DIR}")
    except Exception as exc:
        log(f"Failed to save font {target_file}: {exc}")


def ensure_template_fonts_available() -> None:
    config = load_config()
    for template in config.get("templates", []):
        if not isinstance(template, dict):
            continue

        font_config = template.get("font")
        if isinstance(font_config, dict):
            download_font_assets(font_config)


def get_available_font_names() -> tuple[str, ...]:
    FONTS_DIR.mkdir(parents=True, exist_ok=True)

    font_names = sorted({path.name for path in FONTS_DIR.glob("*.ttf") if path.is_file()})
    if font_names:
        return tuple(font_names)

    fallback_names: set[str] = set()
    for template in load_config().get("templates", []):
        if not isinstance(template, dict):
            continue
        for key in ("font", "title", "subtitle"):
            for candidate in get_font_candidates(template.get(key, {})):
                if candidate.lower().endswith(".ttf"):
                    fallback_names.add(Path(candidate).name)

    return tuple(sorted(fallback_names))


def get_settings_font_options() -> tuple[str, ...]:
    return (TEMPLATE_DEFAULT_FONT, *get_available_font_names())


def load_font(font_config: Any, size: int):
    _, _, _, ImageFont = require_pillow()
    download_font_assets(font_config)
    font_candidates = get_font_candidates(font_config)

    for candidate in iter_font_candidates(font_candidates):
        try:
            return ImageFont.truetype(str(candidate), size=size)
        except OSError:
            continue

    return ImageFont.load_default()


def measure_text(draw, text: str, font, multiline_spacing: int, outline_thickness: int) -> tuple[int, int, tuple[int, int, int, int]]:
    if not text:
        return 0, 0, (0, 0, 0, 0)

    bbox = draw.multiline_textbbox(
        (0, 0),
        text,
        font=font,
        align="center",
        spacing=multiline_spacing,
        stroke_width=max(0, outline_thickness),
    )
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    return width, height, bbox


def fit_font(draw, text: str, font_config: Any, size: int, min_size: int, max_width: int, multiline_spacing: int, outline_thickness: int):
    current_size = max(min_size, size)

    while current_size >= min_size:
        font = load_font(font_config, current_size)
        width, height, bbox = measure_text(draw, text, font, multiline_spacing, outline_thickness)
        if not text or width <= max_width:
            return font, width, height, bbox, current_size
        current_size -= 1

    font = load_font(font_config, min_size)
    width, height, bbox = measure_text(draw, text, font, multiline_spacing, outline_thickness)
    return font, width, height, bbox, min_size


def apply_int_override(target: dict[str, Any], key: str, value: Any) -> None:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and int(value) >= 0:
        target[key] = int(value)


def apply_string_override(target: dict[str, Any], key: str, value: Any) -> None:
    normalized = normalize_optional_string(value)
    if normalized is not None:
        target[key] = normalized


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


def resolve_text_layout(draw, template: dict[str, Any], title: str, subtitle: str, available_width: int, available_height: int) -> dict[str, Any]:
    text_area = template.get("text_area", {})
    text_outline = template.get("text_outline", {})
    shared_font_config = template.get("font", {})
    title_config = template.get("title", {})
    subtitle_config = template.get("subtitle", {})

    padding_x = get_int(text_area, "padding_x", 20, minimum=0)
    max_width = max(1, available_width - (padding_x * 2))
    block_spacing = get_int(text_area, "block_spacing", 8, minimum=0)
    multiline_spacing = get_int(text_area, "multiline_spacing", 4, minimum=0)
    outline_thickness = get_int(text_outline, "thickness", 0, minimum=0)
    outline_color = get_color(text_outline.get("color"), "#000000")

    title_size = get_int(title_config, "size", 40, minimum=1)
    subtitle_size = get_int(subtitle_config, "size", 32, minimum=1)
    title_min_size = get_int(title_config, "min_size", 18, minimum=1)
    subtitle_min_size = get_int(subtitle_config, "min_size", 16, minimum=1)

    title_font_config = deep_merge_dicts(shared_font_config, title_config) if isinstance(shared_font_config, dict) else title_config
    subtitle_font_config = deep_merge_dicts(shared_font_config, subtitle_config) if isinstance(shared_font_config, dict) else subtitle_config

    title_font, title_width, title_height, title_bbox, title_size = fit_font(
        draw,
        title,
        title_font_config,
        title_size,
        title_min_size,
        max_width,
        multiline_spacing,
        outline_thickness,
    )
    subtitle_font, subtitle_width, subtitle_height, subtitle_bbox, subtitle_size = fit_font(
        draw,
        subtitle,
        subtitle_font_config,
        subtitle_size,
        subtitle_min_size,
        max_width,
        multiline_spacing,
        outline_thickness,
    )

    while True:
        total_height = 0
        if title:
            total_height += title_height
        if subtitle:
            if total_height > 0:
                total_height += block_spacing
            total_height += subtitle_height

        if total_height <= available_height:
            break

        if subtitle and subtitle_size > subtitle_min_size:
            subtitle_size -= 1
            subtitle_font, subtitle_width, subtitle_height, subtitle_bbox, subtitle_size = fit_font(
                draw,
                subtitle,
                subtitle_font_config,
                subtitle_size,
                subtitle_min_size,
                max_width,
                multiline_spacing,
                outline_thickness,
            )
            continue

        if title and title_size > title_min_size:
            title_size -= 1
            title_font, title_width, title_height, title_bbox, title_size = fit_font(
                draw,
                title,
                title_font_config,
                title_size,
                title_min_size,
                max_width,
                multiline_spacing,
                outline_thickness,
            )
            continue

        break

    return {
        "max_width": max_width,
        "block_spacing": block_spacing,
        "multiline_spacing": multiline_spacing,
        "outline_thickness": outline_thickness,
        "outline_color": outline_color,
        "title": {
            "font": title_font,
            "width": title_width,
            "height": title_height,
            "bbox": title_bbox,
            "text": title,
        },
        "subtitle": {
            "font": subtitle_font,
            "width": subtitle_width,
            "height": subtitle_height,
            "bbox": subtitle_bbox,
            "text": subtitle,
        },
    }


def draw_centered_text(draw, region_x: int, region_width: int, y: int, text: str, font, fill: tuple[int, int, int], bbox: tuple[int, int, int, int], multiline_spacing: int, outline_thickness: int, outline_color: tuple[int, int, int]) -> None:
    if not text:
        return

    width = bbox[2] - bbox[0]
    x = int(round(region_x + (region_width - width) / 2 - bbox[0]))
    adjusted_y = int(round(y - bbox[1]))
    draw.multiline_text(
        (x, adjusted_y),
        text,
        font=font,
        fill=fill,
        align="center",
        spacing=multiline_spacing,
        stroke_width=max(0, outline_thickness),
        stroke_fill=outline_color,
    )


def get_layout_total_height(layout: dict[str, Any]) -> int:
    title_layout = layout["title"]
    subtitle_layout = layout["subtitle"]

    total_text_height = 0
    if title_layout["text"]:
        total_text_height += title_layout["height"]
    if subtitle_layout["text"]:
        if total_text_height > 0:
            total_text_height += layout["block_spacing"]
        total_text_height += subtitle_layout["height"]

    return total_text_height


def get_text_region(template: dict[str, Any], canvas_width: int, canvas_height: int, image_x: int, image_y: int, source_width: int, source_height: int) -> dict[str, Any]:
    text_area = template.get("text_area", {})
    text_position = get_text_position_value(template)
    gap_from_image = get_int(text_area, "gap_from_image", 20, minimum=0)
    padding_bottom = get_int(text_area, "padding_bottom", 16, minimum=0)

    overlay_region = {
        "region_x": image_x,
        "region_width": source_width,
        "text_start_y": image_y + padding_bottom,
        "available_text_height": max(1, source_height - (padding_bottom * 2)),
        "vertical_anchor": "center",
    }

    if text_position == "overlay":
        return overlay_region

    if text_position == "above":
        available_text_height = image_y - gap_from_image - padding_bottom
        if available_text_height <= 1:
            fallback = overlay_region.copy()
            fallback["vertical_anchor"] = "top"
            return fallback

        return {
            "region_x": 0,
            "region_width": canvas_width,
            "text_start_y": padding_bottom,
            "available_text_height": max(1, available_text_height),
            "vertical_anchor": "center",
        }

    available_text_height = canvas_height - (image_y + source_height + gap_from_image) - padding_bottom
    if available_text_height <= 1:
        fallback = overlay_region.copy()
        fallback["vertical_anchor"] = "bottom"
        return fallback

    return {
        "region_x": 0,
        "region_width": canvas_width,
        "text_start_y": image_y + source_height + gap_from_image,
        "available_text_height": max(1, available_text_height),
        "vertical_anchor": "center",
    }


def get_text_block_start(region_start_y: int, available_height: int, total_text_height: int, vertical_anchor: str) -> int:
    free_space = max(0, available_height - total_text_height)
    if vertical_anchor == "top":
        return region_start_y
    if vertical_anchor == "bottom":
        return region_start_y + free_space
    return region_start_y + (free_space // 2)


def tensor_to_pil(image_tensor):
    Image, _, _, _ = require_pillow()
    torch = require_torch()

    tensor = image_tensor.detach().cpu()
    if tensor.ndim != 3:
        raise RuntimeError(f"Expected an IMAGE tensor with 3 dimensions, got shape {tuple(tensor.shape)}")

    if tensor.shape[-1] == 4:
        tensor = tensor[..., :3]
    elif tensor.shape[-1] == 1:
        tensor = tensor.repeat(1, 1, 3)
    elif tensor.shape[-1] != 3:
        raise RuntimeError(f"Unsupported channel count {tensor.shape[-1]} for meme generation")

    tensor = tensor.to(dtype=torch.float32).clamp(0.0, 1.0)
    np = require_numpy()
    array = (tensor.numpy() * 255.0).round().astype(np.uint8)
    return Image.fromarray(array, mode="RGB")


def pil_to_tensor(image):
    torch = require_torch()
    np = require_numpy()

    array = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    return torch.from_numpy(array)


def render_classic_demotivator(image, template: dict[str, Any], title: str, subtitle: str):
    Image, _, ImageDraw, _ = require_pillow()

    source = image.convert("RGB")
    source_width, source_height = source.size

    canvas_extra = template.get("canvas_extra", {})
    image_offset = template.get("image_offset", {})
    frame = template.get("frame", {})

    image_x = get_int(image_offset, "x", 20, minimum=0)
    image_y = get_int(image_offset, "y", 20, minimum=0)
    frame_gap = get_int(frame, "gap", 1, minimum=0)
    frame_thickness = get_int(frame, "thickness", 1, minimum=0)
    extra_width = get_int(canvas_extra, "width", 40, minimum=0)
    extra_height = get_int(canvas_extra, "height", 140, minimum=0)

    minimum_width = image_x + source_width + frame_gap + frame_thickness
    minimum_height = image_y + source_height + 1
    canvas_width = max(source_width + extra_width, minimum_width)
    canvas_height = max(source_height + extra_height, minimum_height)
    background_color = get_color(template.get("background_color"), "#000000")
    text_color = get_color(template.get("text_color"), "#FFFFFF")
    frame_color = get_color(frame.get("color"), "#FFFFFF")

    canvas = Image.new("RGB", (canvas_width, canvas_height), color=background_color)
    canvas.paste(source, (image_x, image_y))
    draw = ImageDraw.Draw(canvas)

    if frame_thickness > 0:
        frame_left = image_x - frame_gap - frame_thickness
        frame_top = image_y - frame_gap - frame_thickness
        frame_right = image_x + source_width + frame_gap + frame_thickness - 1
        frame_bottom = image_y + source_height + frame_gap + frame_thickness - 1
        for offset in range(frame_thickness):
            draw.rectangle(
                (
                    frame_left + offset,
                    frame_top + offset,
                    frame_right - offset,
                    frame_bottom - offset,
                ),
                outline=frame_color,
            )

    region = get_text_region(template, canvas_width, canvas_height, image_x, image_y, source_width, source_height)
    region_x = region["region_x"]
    region_width = region["region_width"]
    text_start_y = region["text_start_y"]
    available_text_height = region["available_text_height"]
    vertical_anchor = region["vertical_anchor"]

    layout = resolve_text_layout(draw, template, title, subtitle, region_width, available_text_height)
    total_text_height = get_layout_total_height(layout)

    title_layout = layout["title"]
    subtitle_layout = layout["subtitle"]
    current_y = get_text_block_start(text_start_y, available_text_height, total_text_height, vertical_anchor)

    if title_layout["text"]:
        draw_centered_text(
            draw,
            region_x,
            region_width,
            current_y,
            title_layout["text"],
            title_layout["font"],
            text_color,
            title_layout["bbox"],
            layout["multiline_spacing"],
            layout["outline_thickness"],
            layout["outline_color"],
        )
        current_y += title_layout["height"]

    if subtitle_layout["text"]:
        if title_layout["text"]:
            current_y += layout["block_spacing"]
        draw_centered_text(
            draw,
            region_x,
            region_width,
            current_y,
            subtitle_layout["text"],
            subtitle_layout["font"],
            text_color,
            subtitle_layout["bbox"],
            layout["multiline_spacing"],
            layout["outline_thickness"],
            layout["outline_color"],
        )

    return canvas


def render_meme(image, template: dict[str, Any], title: str, subtitle: str):
    template_type = template.get("type", "")
    if template_type == "classic_demotivator":
        return render_classic_demotivator(image, template, title, subtitle)

    raise RuntimeError(f"Unsupported meme template type: {template_type}")


class ArtemKo7vMememizatorSettings:
    CATEGORY = "ArtemKo7v"
    RETURN_TYPES = (SETTINGS_TYPE,)
    RETURN_NAMES = ("settings",)
    FUNCTION = "build_settings"

    @classmethod
    def INPUT_TYPES(cls):
        defaults = get_settings_defaults()
        return {
            "required": {
                "template_name": (get_template_names(),),
                "background": ("STRING", {"default": defaults["background"], "multiline": False}),
                "text": ("STRING", {"default": defaults["text"], "multiline": False}),
                "padding_x": ("INT", {"default": defaults["padding_x"], "min": -1, "max": 8192}),
                "padding_y": ("INT", {"default": defaults["padding_y"], "min": -1, "max": 8192}),
                "frame_color": ("STRING", {"default": defaults["frame_color"], "multiline": False}),
                "frame_gap": ("INT", {"default": defaults["frame_gap"], "min": -1, "max": 8192}),
                "frame_thickness": ("INT", {"default": defaults["frame_thickness"], "min": -1, "max": 8192}),
                "text_padding_x": ("INT", {"default": defaults["text_padding_x"], "min": -1, "max": 8192}),
                "text_padding_bottom": ("INT", {"default": defaults["text_padding_bottom"], "min": -1, "max": 8192}),
                "text_position": (TEXT_POSITION_OPTIONS,),
                "outline_color": ("STRING", {"default": defaults["outline_color"], "multiline": False}),
                "outline_thickness": ("INT", {"default": defaults["outline_thickness"], "min": -1, "max": 8192}),
                "gap_from_image": ("INT", {"default": defaults["gap_from_image"], "min": -1, "max": 8192}),
                "block_spacing": ("INT", {"default": defaults["block_spacing"], "min": -1, "max": 8192}),
                "multiline_spacing": ("INT", {"default": defaults["multiline_spacing"], "min": -1, "max": 8192}),
                "extra_width": ("INT", {"default": defaults["extra_width"], "min": -1, "max": 8192}),
                "extra_height": ("INT", {"default": defaults["extra_height"], "min": -1, "max": 8192}),
                "title_size": ("INT", {"default": defaults["title_size"], "min": -1, "max": 8192}),
                "title_min_size": ("INT", {"default": defaults["title_min_size"], "min": -1, "max": 8192}),
                "subtitle_size": ("INT", {"default": defaults["subtitle_size"], "min": -1, "max": 8192}),
                "subtitle_min_size": ("INT", {"default": defaults["subtitle_min_size"], "min": -1, "max": 8192}),
                "font_name": (get_settings_font_options(),),
            }
        }

    def build_settings(
        self,
        template_name,
        background,
        text,
        padding_x,
        padding_y,
        frame_color,
        frame_gap,
        frame_thickness,
        text_padding_x,
        text_padding_bottom,
        text_position,
        outline_color,
        outline_thickness,
        gap_from_image,
        block_spacing,
        multiline_spacing,
        extra_width,
        extra_height,
        title_size,
        title_min_size,
        subtitle_size,
        subtitle_min_size,
        font_name,
    ):
        return (
            {
                "template_name": template_name,
                "background": background,
                "text": text,
                "padding_x": padding_x,
                "padding_y": padding_y,
                "frame_color": frame_color,
                "frame_gap": frame_gap,
                "frame_thickness": frame_thickness,
                "text_padding_x": text_padding_x,
                "text_padding_bottom": text_padding_bottom,
                "text_position": text_position,
                "outline_color": outline_color,
                "outline_thickness": outline_thickness,
                "gap_from_image": gap_from_image,
                "block_spacing": block_spacing,
                "multiline_spacing": multiline_spacing,
                "extra_width": extra_width,
                "extra_height": extra_height,
                "title_size": title_size,
                "title_min_size": title_min_size,
                "subtitle_size": subtitle_size,
                "subtitle_min_size": subtitle_min_size,
                "font_name": font_name,
            },
        )


class ArtemKo7vMememizator:
    CATEGORY = "ArtemKo7v"
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "mememizate"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "template": (get_template_names(),),
                "title": ("STRING", {"default": "", "multiline": False}),
                "subtitle": ("STRING", {"default": "", "multiline": True}),
            },
            "optional": {
                "settings": (SETTINGS_TYPE,),
            },
        }

    def mememizate(self, image, template, title, subtitle, settings=None):
        torch = require_torch()

        title_text = normalize_text(title)
        subtitle_text = normalize_text(subtitle)
        template_config = apply_settings_override(get_template_config(template), settings)

        if image.ndim == 3:
            single_image = tensor_to_pil(image)
            rendered = render_meme(single_image, template_config, title_text, subtitle_text)
            return (pil_to_tensor(rendered),)

        if image.ndim != 4:
            raise RuntimeError(f"Expected IMAGE tensor with 3 or 4 dimensions, got shape {tuple(image.shape)}")

        rendered_batch = []
        for index in range(image.shape[0]):
            single_image = tensor_to_pil(image[index])
            rendered = render_meme(single_image, template_config, title_text, subtitle_text)
            rendered_batch.append(pil_to_tensor(rendered))

        return (torch.stack(rendered_batch, dim=0).cpu(),)


NODE_CLASS_MAPPINGS = {
    "ArtemKo7vMememizator": ArtemKo7vMememizator,
    "ArtemKo7vMememizatorSettings": ArtemKo7vMememizatorSettings,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ArtemKo7vMememizator": "Mememizator",
    "ArtemKo7vMememizatorSettings": "Mememizator Settings",
}
