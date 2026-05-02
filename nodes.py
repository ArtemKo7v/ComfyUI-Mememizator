from .mememizator.config import get_template_config, get_template_names
from .mememizator.constants import SETTINGS_TYPE, TEXT_POSITION_OPTIONS
from .mememizator.dependencies import require_torch
from .mememizator.fonts import get_settings_font_options
from .mememizator.render import render_meme
from .mememizator import server as _server
from .mememizator.settings import apply_settings_override, get_settings_defaults
from .mememizator.tensor import pil_to_tensor, tensor_to_pil
from .mememizator.utils import normalize_text


class ArtemKo7vMememizatorSettings:
    CATEGORY = "ArtemKo7v"
    RETURN_TYPES = (SETTINGS_TYPE,)
    RETURN_NAMES = ("settings",)
    FUNCTION = "build_settings"

    # Defines the ComfyUI inputs for the settings node.
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

    # Builds a settings payload from widget values.
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

    # Defines the ComfyUI inputs for the meme node.
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

    # Renders meme images from input tensors and template settings.
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
