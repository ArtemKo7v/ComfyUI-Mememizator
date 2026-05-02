from typing import Any

from .dependencies import require_pillow
from .fonts import load_font
from .settings import get_text_position_value
from .utils import deep_merge_dicts, get_int


# Parses a color value with a fallback.
def get_color(value: Any, fallback: str = "#FFFFFF") -> tuple[int, int, int]:
    _, ImageColor, _, _ = require_pillow()

    if isinstance(value, str):
        try:
            return ImageColor.getrgb(value)
        except ValueError:
            pass

    return ImageColor.getrgb(fallback)


# Measures multiline text dimensions.
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


# Finds the largest font size that fits the target width.
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


# Resolves fitted title and subtitle layout data.
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


# Draws centered multiline text inside a horizontal region.
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


# Calculates the total height of the rendered text block.
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


# Calculates the canvas region used for title and subtitle text.
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


# Calculates the vertical start position for a text block.
def get_text_block_start(region_start_y: int, available_height: int, total_text_height: int, vertical_anchor: str) -> int:
    free_space = max(0, available_height - total_text_height)
    if vertical_anchor == "top":
        return region_start_y
    if vertical_anchor == "bottom":
        return region_start_y + free_space
    return region_start_y + (free_space // 2)


# Renders the classic demotivator template.
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


# Dispatches rendering based on the template type.
def render_meme(image, template: dict[str, Any], title: str, subtitle: str):
    template_type = template.get("type", "")
    if template_type == "classic_demotivator":
        return render_classic_demotivator(image, template, title, subtitle)

    raise RuntimeError(f"Unsupported meme template type: {template_type}")


