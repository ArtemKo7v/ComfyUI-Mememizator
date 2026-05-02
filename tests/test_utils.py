import unittest

from mememizator.utils import deep_merge_dicts, get_int, normalize_optional_string, normalize_text


class UtilsTests(unittest.TestCase):
    # Recursively merges dictionaries without mutating inputs.
    def test_deep_merge_dicts_merges_without_mutating_inputs(self):
        base = {"a": {"b": 1, "c": 2}, "d": 3}
        override = {"a": {"b": 9}, "e": 4}

        merged = deep_merge_dicts(base, override)

        self.assertEqual(merged, {"a": {"b": 9, "c": 2}, "d": 3, "e": 4})
        self.assertEqual(base, {"a": {"b": 1, "c": 2}, "d": 3})
        self.assertEqual(override, {"a": {"b": 9}, "e": 4})

    # Reads integer-like values while rejecting bools and invalid values.
    def test_get_int_handles_bounds_and_invalid_values(self):
        self.assertEqual(get_int({"value": 5.9}, "value", 1), 5)
        self.assertEqual(get_int({"value": -3}, "value", 1, minimum=0), 0)
        self.assertEqual(get_int({"value": True}, "value", 1), 1)
        self.assertEqual(get_int({"value": "5"}, "value", 1), 1)
        self.assertEqual(get_int({}, "value", 1), 1)

    # Normalizes rendered text input.
    def test_normalize_text_strips_outer_whitespace_and_normalizes_newlines(self):
        self.assertEqual(normalize_text("  title  \r\nsecond  \rthird\n\n"), "title\nsecond\nthird")
        self.assertEqual(normalize_text(None), "")

    # Converts blank optional strings to None.
    def test_normalize_optional_string_returns_none_for_blank_values(self):
        self.assertEqual(normalize_optional_string(" value "), "value")
        self.assertIsNone(normalize_optional_string("   "))
        self.assertIsNone(normalize_optional_string(None))


if __name__ == "__main__":
    unittest.main()
