import copy
import json
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from mememizator import config
from mememizator.constants import DEFAULT_CONFIG


# Returns the built-in default config without shared references.
def default_config_copy():
    return copy.deepcopy(DEFAULT_CONFIG)


class ConfigTests(unittest.TestCase):
    # Provides both built-in templates in the default config.
    def test_default_config_includes_classic_meme(self):
        template_names = [template["name"] for template in DEFAULT_CONFIG["templates"]]

        self.assertIn("Classic Demotivator", template_names)
        self.assertIn("Classic Meme", template_names)

        classic_meme = next(template for template in DEFAULT_CONFIG["templates"] if template["name"] == "Classic Meme")
        self.assertEqual(classic_meme["type"], "classic_meme")
        self.assertEqual(classic_meme["text_area"]["position"], "overlay")
        self.assertEqual(len(classic_meme["text_lines"]), 4)

    # Normalizes invalid config input to the default config.
    def test_normalize_config_uses_defaults_for_invalid_input(self):
        with patch.object(config, "load_packaged_default_config", default_config_copy):
            self.assertEqual(config.normalize_config(None), DEFAULT_CONFIG)
            self.assertEqual(config.normalize_config({"templates": "bad"}), DEFAULT_CONFIG)

    # Merges user template overrides with the matching default template.
    def test_normalize_config_merges_known_template(self):
        with patch.object(config, "load_packaged_default_config", default_config_copy):
            normalized = config.normalize_config(
                {
                    "templates": [
                        {
                            "name": "Classic Demotivator",
                            "type": "classic_demotivator",
                            "text_color": "#FF0000",
                            "frame": {"thickness": 9},
                        }
                    ]
                }
            )

        template = normalized["templates"][0]
        self.assertEqual(template["text_color"], "#FF0000")
        self.assertEqual(template["frame"]["thickness"], 9)
        self.assertEqual(template["frame"]["gap"], DEFAULT_CONFIG["templates"][0]["frame"]["gap"])
        self.assertEqual(template["font"], DEFAULT_CONFIG["templates"][0]["font"])
        self.assertEqual(normalized["templates"][1]["name"], "Classic Meme")

    # Loads and normalizes config files from the configured user path.
    def test_load_config_normalizes_user_config(self):
        temp_path = Path("tests") / "tmp_config_case"
        if temp_path.exists():
            shutil.rmtree(temp_path)

        try:
            temp_path.mkdir()
            config_dir = temp_path / "ComfyUI-Mememizator"
            config_path = config_dir / "config.json"
            config_dir.mkdir()
            config_path.write_text(
                json.dumps(
                    {
                        "templates": [
                            {
                                "name": "Classic Demotivator",
                                "type": "classic_demotivator",
                                "frame": {"gap": 12},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with (
                patch.object(config, "CONFIG_DIR", config_dir),
                patch.object(config, "CONFIG_PATH", config_path),
                patch.object(config, "PACKAGE_CONFIG_PATH", temp_path / "missing-config.json"),
                patch.object(config, "load_packaged_default_config", default_config_copy),
                patch.object(config, "log"),
            ):
                loaded = config.load_config()

            saved = json.loads(config_path.read_text(encoding="utf-8"))
        finally:
            shutil.rmtree(temp_path, ignore_errors=True)

        self.assertEqual(loaded, saved)
        self.assertEqual(loaded["templates"][0]["frame"]["gap"], 12)
        self.assertEqual(loaded["templates"][1]["name"], "Classic Meme")
        self.assertEqual(
            loaded["templates"][0]["frame"]["thickness"],
            DEFAULT_CONFIG["templates"][0]["frame"]["thickness"],
        )

    # Returns the named template and falls back to the first template.
    def test_get_template_config_returns_named_or_first_template(self):
        templates = [
            {"name": "First", "type": "classic_demotivator"},
            {"name": "Second", "type": "classic_demotivator"},
        ]
        with patch.object(config, "load_config", lambda: {"templates": templates}):
            self.assertEqual(config.get_template_config("Second"), templates[1])
            self.assertEqual(config.get_template_config("Missing"), templates[0])


if __name__ == "__main__":
    unittest.main()
