from typing import Any

from .constants import TEXT_LINE_ALIGN_OPTIONS, TEXT_LINE_VERTICAL_POSITION_OPTIONS
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
def measure_text(draw, text: str, font, multiline_spacing: int, outline_thickness: int, align: str = "center") -> tuple[int, int, tuple[int, int, int, int]]:
    if not text:
        return 0, 0, (0, 0, 0, 0)

    bbox = draw.multiline_textbbox(
        (0, 0),
        text,
        font=font,
        align=align,
        spacing=multiline_spacing,
        stroke_width=max(0, outline_thickness),
    )
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    return width, height, bbox


# Finds the largest font size that fits the target width.
def fit_font(draw, text: str, font_config: Any, size: int, min_size: int, max_width: int, multiline_spacing: int, outline_thickness: int, align: str = "center"):
    current_size = max(min_size, size)

    while current_size >= min_size:
        font = load_font(font_config, current_size)
        width, height, bbox = measure_text(draw, text, font, multiline_spacing, outline_thickness, align)
        if not text or width <= max_width:
            return font, width, height, bbox, current_size
        current_size -= 1

    font = load_font(font_config, min_size)
    width, height, bbox = measure_text(draw, text, font, multiline_spacing, outline_thickness, align)
    return font, width, height, bbox, min_size


# Returns a supported per-line vertical position.
def get_line_vertical_position(value: Any) -> str:
    if isinstance(value, str) and value in TEXT_LINE_VERTICAL_POSITION_OPTIONS:
        return value
    return "center"


# Returns a supported per-line horizontal alignment.
def get_line_align(value: Any) -> str:
    if isinstance(value, str) and value in TEXT_LINE_ALIGN_OPTIONS:
        return value
    return "center"


# Converts legacy title/subtitle sections into generic line configs.
def get_template_text_lines(template: dict[str, Any]) -> list[dict[str, Any]]:
    lines = template.get("text_lines")
    if isinstance(lines, list):
        return [line for line in lines[:4] if isinstance(line, dict)]

    return [
        {
            "source": "title",
            "vertical_position": "center",
            "align": "center",
            **(template.get("title", {}) if isinstance(template.get("title"), dict) else {}),
        },
        {
            "source": "subtitle",
            "vertical_position": "center",
            "align": "center",
            **(template.get("subtitle", {}) if isinstance(template.get("subtitle"), dict) else {}),
        },
    ]


# Resolves fitted generic text-line layout data.
def resolve_text_lines_layout(draw, template: dict[str, Any], text_values: dict[str, str], available_width: int, available_height: int) -> dict[str, Any]:
    text_area = template.get("text_area", {})
    text_outline = template.get("text_outline", {})
    shared_font_config = template.get("font", {})

    padding_x = get_int(text_area, "padding_x", 20, minimum=0)
    max_width = max(1, available_width - (padding_x * 2))
    block_spacing = get_int(text_area, "block_spacing", 8, minimum=0)
    multiline_spacing = get_int(text_area, "multiline_spacing", 4, minimum=0)
    outline_thickness = get_int(text_outline, "thickness", 0, minimum=0)
    outline_color = get_color(text_outline.get("color"), "#000000")

    layouts: list[dict[str, Any]] = []
    for line_config in get_template_text_lines(template):
        source = line_config.get("source", "")
        text = text_values.get(source, "") if isinstance(source, str) else ""
        if not text:
            continue

        align = get_line_align(line_config.get("align"))
        size = get_int(line_config, "size", 40, minimum=1)
        min_size = get_int(line_config, "min_size", 18, minimum=1)
        font_config = deep_merge_dicts(shared_font_config, line_config) if isinstance(shared_font_config, dict) else line_config
        font, width, height, bbox, resolved_size = fit_font(
            draw,
            text,
            font_config,
            size,
            min_size,
            max_width,
            multiline_spacing,
            outline_thickness,
            align,
        )
        layouts.append(
            {
                "font": font,
                "width": width,
                "height": height,
                "bbox": bbox,
                "text": text,
                "size": resolved_size,
                "min_size": min_size,
                "font_config": font_config,
                "vertical_position": get_line_vertical_position(line_config.get("vertical_position")),
                "align": align,
            }
        )

    while get_layout_total_height({"lines": layouts, "block_spacing": block_spacing}) > available_height:
        shrinkable = next((line for line in reversed(layouts) if line["size"] > line["min_size"]), None)
        if shrinkable is None:
            break

        shrinkable["size"] -= 1
        font, width, height, bbox, resolved_size = fit_font(
            draw,
            shrinkable["text"],
            shrinkable["font_config"],
            shrinkable["size"],
            shrinkable["min_size"],
            max_width,
            multiline_spacing,
            outline_thickness,
            shrinkable["align"],
        )
        shrinkable.update({"font": font, "width": width, "height": height, "bbox": bbox, "size": resolved_size})

    return {
        "max_width": max_width,
        "block_spacing": block_spacing,
        "multiline_spacing": multiline_spacing,
        "outline_thickness": outline_thickness,
        "outline_color": outline_color,
        "lines": layouts,
    }


# Draws multiline text inside a horizontal region.
def draw_aligned_text(draw, region_x: int, region_width: int, y: int, text: str, font, fill: tuple[int, int, int], bbox: tuple[int, int, int, int], multiline_spacing: int, outline_thickness: int, outline_color: tuple[int, int, int], align: str) -> None:
    if not text:
        return

    width = bbox[2] - bbox[0]
    if align == "left":
        x = region_x - bbox[0]
    elif align == "right":
        x = region_x + region_width - width - bbox[0]
    else:
        x = int(round(region_x + (region_width - width) / 2 - bbox[0]))
    adjusted_y = int(round(y - bbox[1]))
    draw.multiline_text(
        (x, adjusted_y),
        text,
        font=font,
        fill=fill,
        align=align,
        spacing=multiline_spacing,
        stroke_width=max(0, outline_thickness),
        stroke_fill=outline_color,
    )


# Calculates the total height of the rendered text block.
def get_layout_total_height(layout: dict[str, Any]) -> int:
    total_text_height = 0
    for line in layout.get("lines", []):
        if not line.get("text"):
            continue
        if total_text_height > 0:
            total_text_height += layout["block_spacing"]
        total_text_height += line["height"]

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


# Draws all configured text lines inside a region.
def draw_text_lines(draw, template: dict[str, Any], text_values: dict[str, str], region: dict[str, Any], text_color: tuple[int, int, int]) -> None:
    region_x = region["region_x"]
    region_width = region["region_width"]
    text_start_y = region["text_start_y"]
    available_text_height = region["available_text_height"]

    layout = resolve_text_lines_layout(draw, template, text_values, region_width, available_text_height)
    for vertical_position in ("top", "center", "bottom"):
        lines = [line for line in layout["lines"] if line["vertical_position"] == vertical_position]
        if not lines:
            continue

        total_text_height = get_layout_total_height({"lines": lines, "block_spacing": layout["block_spacing"]})
        current_y = get_text_block_start(text_start_y, available_text_height, total_text_height, vertical_position)
        for index, line in enumerate(lines):
            if index > 0:
                current_y += layout["block_spacing"]
            draw_aligned_text(
                draw,
                region_x,
                region_width,
                current_y,
                line["text"],
                line["font"],
                text_color,
                line["bbox"],
                layout["multiline_spacing"],
                layout["outline_thickness"],
                layout["outline_color"],
                line["align"],
            )
            current_y += line["height"]


# Renders a meme template from generic canvas and text configuration.
def render_configured_meme(image, template: dict[str, Any], text_values: dict[str, str]):
    Image, _, ImageDraw, _ = require_pillow()

    source = image.convert("RGB")
    source_width, source_height = source.size

    canvas_extra = template.get("canvas_extra", {})
    image_offset = template.get("image_offset", {})
    frame = template.get("frame", {})

    image_x = get_int(image_offset, "x", 0, minimum=0)
    image_y = get_int(image_offset, "y", 0, minimum=0)
    frame_gap = get_int(frame, "gap", 1, minimum=0)
    frame_thickness = get_int(frame, "thickness", 0, minimum=0)
    extra_width = get_int(canvas_extra, "width", image_x * 2, minimum=0)
    extra_height = get_int(canvas_extra, "height", image_y * 2, minimum=0)

    frame_extent = frame_gap + frame_thickness if frame_thickness > 0 else 0
    minimum_width = image_x + source_width + frame_extent
    minimum_height = image_y + source_height + frame_extent
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
    draw_text_lines(draw, template, text_values, region, text_color)

    return canvas


# Dispatches rendering based on the template type.
def render_meme(image, template: dict[str, Any], title: str, subtitle: str, text_3: str = "", text_4: str = ""):
    template_type = template.get("type", "")
    if template_type in ("classic_demotivator", "classic_meme"):
        return render_configured_meme(
            image,
            template,
            {
                "title": title,
                "subtitle": subtitle,
                "text_3": text_3,
                "text_4": text_4,
            },
        )

    raise RuntimeError(f"Unsupported meme template type: {template_type}")


