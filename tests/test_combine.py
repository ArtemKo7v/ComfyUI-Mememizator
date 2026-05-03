import unittest

from mememizator.combine import combine_images
from mememizator.dependencies import require_pillow


def make_image(width, height, color):
    Image, _, _, _ = require_pillow()
    return Image.new("RGB", (width, height), color=color)


class CombineImagesTests(unittest.TestCase):
    # Combines images in one horizontal row with padding.
    def test_combine_horizontal(self):
        result = combine_images(
            [
                make_image(10, 20, "#FF0000"),
                make_image(30, 10, "#00FF00"),
            ],
            "horizontal",
            padding=5,
        )

        self.assertEqual(result.size, (45, 20))

    # Combines images in one vertical column with padding.
    def test_combine_vertical(self):
        result = combine_images(
            [
                make_image(10, 20, "#FF0000"),
                make_image(30, 10, "#00FF00"),
            ],
            "vertical",
            padding=5,
        )

        self.assertEqual(result.size, (30, 35))

    # Combines images in a row-major 2x2 grid.
    def test_combine_grid_2x2(self):
        result = combine_images(
            [
                make_image(10, 20, "#FF0000"),
                make_image(30, 10, "#00FF00"),
                make_image(20, 15, "#0000FF"),
            ],
            "2x2",
            padding=5,
        )

        self.assertEqual(result.size, (55, 40))

    # Fits the combined image into configured maximum dimensions.
    def test_combine_resizes_to_maximum_dimensions(self):
        result = combine_images(
            [
                make_image(100, 50, "#FF0000"),
                make_image(100, 50, "#00FF00"),
            ],
            "horizontal",
            max_width=100,
            max_height=100,
        )

        self.assertEqual(result.size, (100, 25))


if __name__ == "__main__":
    unittest.main()
