import copy
import json
import os
import shutil
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
USER_DIR = Path(os.getcwd()) / "user" / "default"
CONFIG_DIR = USER_DIR / "ComfyUI-Mememizator"
CONFIG_PATH = CONFIG_DIR / "config.json"
PACKAGE_CONFIG_PATH = BASE_DIR / "config.json"
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
                "gap": 1,
                "thickness": 1,
            },
            "text_area": {
                "padding_x": 20,
                "padding_bottom": 16,
                "gap_from_image": 20,
                "block_spacing": 8,
                "multiline_spacing": 4,
            },
            "title": {
                "size": 40,
                "min_size": 18,
                "font_candidates": [
                    "times.ttf",
                    "Times New Roman.ttf",
                    "times new roman.ttf",
                    "DejaVuSerif.ttf",
                    "LiberationSerif-Regular.ttf",
                    "NotoSerif-Regular.ttf",
                ],
            },
            "subtitle": {
                "size": 32,
                "min_size": 16,
                "font_candidates": [
                    "times.ttf",
                    "Times New Roman.ttf",
                    "times new roman.ttf",
                    "DejaVuSerif.ttf",
                    "LiberationSerif-Regular.ttf",
                    "NotoSerif-Regular.ttf",
                ],
            },
        }
    ]
}


def log(message: str) -> None:
    print(f"[ComfyUI-Mememizator]: {message}")


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
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


def load_packaged_default_config() -> dict[str, Any]:
    if PACKAGE_CONFIG_PATH.exists():
        try:
            return read_json(PACKAGE_CONFIG_PATH)
        except (OSError, json.JSONDecodeError) as exc:
            log(f"Failed to read packaged config {PACKAGE_CONFIG_PATH}: {exc}")

    return deep_copy_config(DEFAULT_CONFIG)


def normalize_config(config: Any) -> dict[str, Any]:
    default_config = load_packaged_default_config()
    normalized = deep_copy_config(default_config)

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

        valid_templates.append(template)

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


def iter_font_candidates(candidates: list[str] | tuple[str, ...] | str | Any) -> list[Path]:
    if isinstance(candidates, str):
        candidates = [candidates]
    elif not isinstance(candidates, (list, tuple)):
        candidates = []

    common_dirs = [
        BASE_DIR,
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


def load_font(font_candidates: list[str] | tuple[str, ...], size: int):
    _, _, _, ImageFont = require_pillow()

    for candidate in iter_font_candidates(font_candidates):
        try:
            return ImageFont.truetype(str(candidate), size=size)
        except OSError:
            continue

    return ImageFont.load_default()


def measure_text(draw, text: str, font, multiline_spacing: int) -> tuple[int, int, tuple[int, int, int, int]]:
    if not text:
        return 0, 0, (0, 0, 0, 0)

    bbox = draw.multiline_textbbox(
        (0, 0),
        text,
        font=font,
        align="center",
        spacing=multiline_spacing,
    )
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    return width, height, bbox


def fit_font(draw, text: str, font_candidates: list[str] | tuple[str, ...], size: int, min_size: int, max_width: int, multiline_spacing: int):
    current_size = max(min_size, size)

    while current_size >= min_size:
        font = load_font(font_candidates, current_size)
        width, height, bbox = measure_text(draw, text, font, multiline_spacing)
        if not text or width <= max_width:
            return font, width, height, bbox, current_size
        current_size -= 1

    font = load_font(font_candidates, min_size)
    width, height, bbox = measure_text(draw, text, font, multiline_spacing)
    return font, width, height, bbox, min_size


def resolve_text_layout(draw, template: dict[str, Any], title: str, subtitle: str, canvas_width: int, available_height: int) -> dict[str, Any]:
    text_area = template.get("text_area", {})
    title_config = template.get("title", {})
    subtitle_config = template.get("subtitle", {})

    padding_x = get_int(text_area, "padding_x", 20, minimum=0)
    max_width = max(1, canvas_width - (padding_x * 2))
    block_spacing = get_int(text_area, "block_spacing", 8, minimum=0)
    multiline_spacing = get_int(text_area, "multiline_spacing", 4, minimum=0)

    title_size = get_int(title_config, "size", 40, minimum=1)
    subtitle_size = get_int(subtitle_config, "size", 32, minimum=1)
    title_min_size = get_int(title_config, "min_size", 18, minimum=1)
    subtitle_min_size = get_int(subtitle_config, "min_size", 16, minimum=1)
    title_candidates = title_config.get("font_candidates", [])
    subtitle_candidates = subtitle_config.get("font_candidates", [])

    title_font, title_width, title_height, title_bbox, title_size = fit_font(
        draw,
        title,
        title_candidates,
        title_size,
        title_min_size,
        max_width,
        multiline_spacing,
    )
    subtitle_font, subtitle_width, subtitle_height, subtitle_bbox, subtitle_size = fit_font(
        draw,
        subtitle,
        subtitle_candidates,
        subtitle_size,
        subtitle_min_size,
        max_width,
        multiline_spacing,
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
                subtitle_candidates,
                subtitle_size,
                subtitle_min_size,
                max_width,
                multiline_spacing,
            )
            continue

        if title and title_size > title_min_size:
            title_size -= 1
            title_font, title_width, title_height, title_bbox, title_size = fit_font(
                draw,
                title,
                title_candidates,
                title_size,
                title_min_size,
                max_width,
                multiline_spacing,
            )
            continue

        break

    return {
        "max_width": max_width,
        "block_spacing": block_spacing,
        "multiline_spacing": multiline_spacing,
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


def draw_centered_text(draw, canvas_width: int, y: int, text: str, font, fill: tuple[int, int, int], bbox: tuple[int, int, int, int], multiline_spacing: int) -> None:
    if not text:
        return

    width = bbox[2] - bbox[0]
    x = int(round((canvas_width - width) / 2 - bbox[0]))
    adjusted_y = int(round(y - bbox[1]))
    draw.multiline_text(
        (x, adjusted_y),
        text,
        font=font,
        fill=fill,
        align="center",
        spacing=multiline_spacing,
    )


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
    text_area = template.get("text_area", {})

    image_x = get_int(image_offset, "x", 20, minimum=0)
    image_y = get_int(image_offset, "y", 20, minimum=0)
    frame_gap = get_int(frame, "gap", 1, minimum=0)
    frame_thickness = get_int(frame, "thickness", 1, minimum=1)
    gap_from_image = get_int(text_area, "gap_from_image", 20, minimum=0)
    padding_bottom = get_int(text_area, "padding_bottom", 16, minimum=0)
    extra_width = get_int(canvas_extra, "width", 40, minimum=0)
    extra_height = get_int(canvas_extra, "height", 140, minimum=0)

    minimum_width = image_x + source_width + frame_gap + frame_thickness
    minimum_height = image_y + source_height + gap_from_image + padding_bottom + 1
    canvas_width = max(source_width + extra_width, minimum_width)
    canvas_height = max(source_height + extra_height, minimum_height)
    background_color = get_color(template.get("background_color"), "#000000")
    text_color = get_color(template.get("text_color"), "#FFFFFF")
    frame_color = get_color(frame.get("color"), "#FFFFFF")

    canvas = Image.new("RGB", (canvas_width, canvas_height), color=background_color)
    canvas.paste(source, (image_x, image_y))
    draw = ImageDraw.Draw(canvas)

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

    text_start_y = image_y + source_height + gap_from_image
    available_text_height = max(1, canvas_height - text_start_y - padding_bottom)
    layout = resolve_text_layout(draw, template, title, subtitle, canvas_width, available_text_height)

    title_layout = layout["title"]
    subtitle_layout = layout["subtitle"]
    total_text_height = 0
    if title_layout["text"]:
        total_text_height += title_layout["height"]
    if subtitle_layout["text"]:
        if total_text_height > 0:
            total_text_height += layout["block_spacing"]
        total_text_height += subtitle_layout["height"]

    current_y = text_start_y + max(0, (available_text_height - total_text_height) // 2)
    if title_layout["text"]:
        draw_centered_text(
            draw,
            canvas_width,
            current_y,
            title_layout["text"],
            title_layout["font"],
            text_color,
            title_layout["bbox"],
            layout["multiline_spacing"],
        )
        current_y += title_layout["height"]

    if subtitle_layout["text"]:
        if title_layout["text"]:
            current_y += layout["block_spacing"]
        draw_centered_text(
            draw,
            canvas_width,
            current_y,
            subtitle_layout["text"],
            subtitle_layout["font"],
            text_color,
            subtitle_layout["bbox"],
            layout["multiline_spacing"],
        )

    return canvas


def render_meme(image, template: dict[str, Any], title: str, subtitle: str):
    template_type = template.get("type", "")
    if template_type == "classic_demotivator":
        return render_classic_demotivator(image, template, title, subtitle)

    raise RuntimeError(f"Unsupported meme template type: {template_type}")


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
            }
        }

    def mememizate(self, image, template, title, subtitle):
        torch = require_torch()

        title_text = normalize_text(title)
        subtitle_text = normalize_text(subtitle)
        template_config = get_template_config(template)

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
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ArtemKo7vMememizator": "Mememizator",
}
