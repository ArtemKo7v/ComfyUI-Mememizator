import unittest

from mememizator.render import get_text_block_start, get_text_region


# Creates a template with a configurable text position.
def make_template(position, gap=20, padding_bottom=10):
    return {
        "text_area": {
            "position": position,
            "gap_from_image": gap,
            "padding_bottom": padding_bottom,
        }
    }


class RenderLayoutTests(unittest.TestCase):
    # Returns an overlay region when the template requests overlay text.
    def test_get_text_region_overlay(self):
        region = get_text_region(make_template("overlay"), 200, 240, 20, 30, 160, 120)

        self.assertEqual(
            region,
            {
                "region_x": 20,
                "region_width": 160,
                "text_start_y": 40,
                "available_text_height": 100,
                "vertical_anchor": "center",
            },
        )

    # Returns an above-image region when there is enough space.
    def test_get_text_region_above(self):
        region = get_text_region(make_template("above"), 200, 240, 20, 60, 160, 120)

        self.assertEqual(
            region,
            {
                "region_x": 0,
                "region_width": 200,
                "text_start_y": 10,
                "available_text_height": 30,
                "vertical_anchor": "center",
            },
        )

    # Falls back to an overlay region when below-image space is too small.
    def test_get_text_region_below_falls_back_to_overlay(self):
        region = get_text_region(make_template("below"), 200, 170, 20, 30, 160, 120)

        self.assertEqual(region["region_x"], 20)
        self.assertEqual(region["region_width"], 160)
        self.assertEqual(region["vertical_anchor"], "bottom")

    # Calculates text block starts for each vertical anchor.
    def test_get_text_block_start_uses_anchor(self):
        self.assertEqual(get_text_block_start(10, 100, 40, "top"), 10)
        self.assertEqual(get_text_block_start(10, 100, 40, "center"), 40)
        self.assertEqual(get_text_block_start(10, 100, 40, "bottom"), 70)


if __name__ == "__main__":
    unittest.main()
