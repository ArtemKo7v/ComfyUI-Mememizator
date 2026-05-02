import os
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent
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
                    "impact.ttf",
                ],
                "download": {
                    "url": "https://font.download/dl/font/impact.zip",
                    "target_file": "impact.ttf",
                    "archive_member": "impact.ttf",
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
