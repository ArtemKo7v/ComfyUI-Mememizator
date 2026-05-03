from typing import Any

from .dependencies import require_pillow
from .render import get_color


# Resizes an image so it fits configured maximum dimensions.
def fit_combined_image(image, max_width: int, max_height: int):
    if max_width <= 0 and max_height <= 0:
        return image

    width, height = image.size
    scale = 1.0
    if max_width > 0 and width > max_width:
        scale = min(scale, max_width / width)
    if max_height > 0 and height > max_height:
        scale = min(scale, max_height / height)
    if scale >= 1.0:
        return image

    Image, _, _, _ = require_pillow()
    resampling = getattr(Image, "Resampling", Image).LANCZOS
    resized_width = max(1, int(round(width * scale)))
    resized_height = max(1, int(round(height * scale)))
    return image.resize((resized_width, resized_height), resampling)


# Creates a canvas and pastes images centered in their target cells.
def paste_images_in_cells(images: list[Any], cells: list[tuple[int, int, int, int]], background_color: tuple[int, int, int]):
    Image, _, _, _ = require_pillow()
    canvas_width = max(1, max(x + width for x, y, width, height in cells))
    canvas_height = max(1, max(y + height for x, y, width, height in cells))
    canvas = Image.new("RGB", (canvas_width, canvas_height), color=background_color)

    for image, (cell_x, cell_y, cell_width, cell_height) in zip(images, cells):
        source = image.convert("RGB")
        x = cell_x + ((cell_width - source.width) // 2)
        y = cell_y + ((cell_height - source.height) // 2)
        canvas.paste(source, (x, y))

    return canvas


# Combines images in a horizontal row.
def combine_horizontal(images: list[Any], background_color: tuple[int, int, int], padding: int):
    height = max(image.height for image in images)
    cells: list[tuple[int, int, int, int]] = []
    x = 0
    for image in images:
        cells.append((x, 0, image.width, height))
        x += image.width + padding
    return paste_images_in_cells(images, cells, background_color)


# Combines images in a vertical column.
def combine_vertical(images: list[Any], background_color: tuple[int, int, int], padding: int):
    width = max(image.width for image in images)
    cells: list[tuple[int, int, int, int]] = []
    y = 0
    for image in images:
        cells.append((0, y, width, image.height))
        y += image.height + padding
    return paste_images_in_cells(images, cells, background_color)


# Combines images in a row-major 2x2 grid.
def combine_grid_2x2(images: list[Any], background_color: tuple[int, int, int], padding: int):
    rows = [images[:2], images[2:4]]
    rows = [row for row in rows if row]
    column_widths = [
        max((row[column].width for row in rows if len(row) > column), default=0)
        for column in range(2)
    ]
    row_heights = [max(image.height for image in row) for row in rows]

    cells: list[tuple[int, int, int, int]] = []
    y = 0
    for row_index, row in enumerate(rows):
        x = 0
        for column_index, _image in enumerate(row):
            cells.append((x, y, column_widths[column_index], row_heights[row_index]))
            x += column_widths[column_index] + padding
        y += row_heights[row_index] + padding

    return paste_images_in_cells(images, cells, background_color)


# Combines up to four PIL images into one image.
def combine_images(
    images: list[Any],
    layout: str,
    max_width: int = 0,
    max_height: int = 0,
    background: str = "#000000",
    padding: int = 0,
):
    valid_images = [image.convert("RGB") for image in images[:4] if image is not None]
    if not valid_images:
        raise RuntimeError("At least one image is required for Mememizator Combine Images")

    background_color = get_color(background, "#000000")
    normalized_padding = max(0, int(padding))

    if layout == "vertical":
        combined = combine_vertical(valid_images, background_color, normalized_padding)
    elif layout == "2x2":
        combined = combine_grid_2x2(valid_images, background_color, normalized_padding)
    else:
        combined = combine_horizontal(valid_images, background_color, normalized_padding)

    return fit_combined_image(combined, max(0, int(max_width)), max(0, int(max_height)))
