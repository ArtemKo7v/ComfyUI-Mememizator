import unittest

from mememizator.constants import TEMPLATE_DEFAULT_FONT
from mememizator.settings import apply_settings_override, get_text_position_value


# Builds a minimal template for settings override tests.
def make_template():
    return {
        "name": "Classic Demotivator",
        "type": "classic_demotivator",
        "background_color": "#000000",
        "text_color": "#FFFFFF",
        "image_offset": {"x": 20, "y": 20},
        "frame": {"color": "#FFFFFF", "gap": 4, "thickness": 2},
        "text_area": {"position": "below", "padding_x": 20},
        "text_outline": {"color": "#000000", "thickness": 0},
        "canvas_extra": {"width": 40, "height": 140},
        "font": {"font_candidates": ["impact.ttf"], "download": {"url": "example"}},
        "title": {"size": 128, "min_size": 64},
        "subtitle": {"size": 64, "min_size": 32},
    }


class SettingsTests(unittest.TestCase):
    # Applies valid settings overrides and ignores sentinel values.
    def test_apply_settings_override_applies_valid_values(self):
        result = apply_settings_override(
            make_template(),
            {
                "background": "#111111",
                "text": "#EEEEEE",
                "padding_x": 30,
                "padding_y": -1,
                "frame_color": "#123456",
                "frame_gap": 8,
                "frame_thickness": -1,
                "text_position": "overlay",
                "outline_thickness": 3,
                "extra_width": 100,
                "title_size": 72,
                "font_name": "custom.ttf",
            },
        )

        self.assertEqual(result["background_color"], "#111111")
        self.assertEqual(result["text_color"], "#EEEEEE")
        self.assertEqual(result["image_offset"]["x"], 30)
        self.assertEqual(result["image_offset"]["y"], 20)
        self.assertEqual(result["frame"]["color"], "#123456")
        self.assertEqual(result["frame"]["gap"], 8)
        self.assertEqual(result["frame"]["thickness"], 2)
        self.assertEqual(result["text_area"]["position"], "overlay")
        self.assertEqual(result["text_outline"]["thickness"], 3)
        self.assertEqual(result["canvas_extra"]["width"], 100)
        self.assertEqual(result["title"]["size"], 72)
        self.assertEqual(result["font"], {"font_candidates": ["custom.ttf"], "download": {}})

    # Leaves font settings unchanged when the template default is selected.
    def test_apply_settings_override_ignores_template_default_font(self):
        template = make_template()
        result = apply_settings_override(template, {"font_name": TEMPLATE_DEFAULT_FONT})

        self.assertEqual(result["font"], template["font"])

    # Falls back to below for invalid text positions.
    def test_get_text_position_value_falls_back_to_below(self):
        self.assertEqual(get_text_position_value({"text_area": {"position": "above"}}), "above")
        self.assertEqual(get_text_position_value({"text_area": {"position": "invalid"}}), "below")
        self.assertEqual(get_text_position_value({}), "below")


if __name__ == "__main__":
    unittest.main()
