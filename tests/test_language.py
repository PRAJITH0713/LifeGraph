"""Static coverage checks for the English and Tamil interface dictionaries."""

import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCALES_FILE = PROJECT_ROOT / "frontend" / "js" / "locales.js"
TRANSLATION_KEY_PATTERN = re.compile(r'^\s+"([^"]+)":', re.MULTILINE)
HTML_TRANSLATION_PATTERN = re.compile(
    r'data-i18n(?:-aria|-placeholder)?="([^"]+)"'
)


class LanguageDictionaryTests(unittest.TestCase):
    def test_english_and_tamil_dictionaries_have_matching_keys(self):
        source = LOCALES_FILE.read_text(encoding="utf-8")
        english = source.split("  en: {", 1)[1].split("\n  },\n  ta: {", 1)[0]
        tamil = source.split("  ta: {", 1)[1].rsplit("\n  }", 1)[0]

        self.assertEqual(
            set(TRANSLATION_KEY_PATTERN.findall(english)),
            set(TRANSLATION_KEY_PATTERN.findall(tamil)),
        )

    def test_template_translation_keys_exist_in_both_dictionaries(self):
        source = LOCALES_FILE.read_text(encoding="utf-8")
        english = source.split("  en: {", 1)[1].split("\n  },\n  ta: {", 1)[0]
        tamil = source.split("  ta: {", 1)[1].rsplit("\n  }", 1)[0]
        available_keys = set(TRANSLATION_KEY_PATTERN.findall(english))
        available_keys.intersection_update(TRANSLATION_KEY_PATTERN.findall(tamil))

        missing = {}
        for template in (PROJECT_ROOT / "frontend").glob("*.html"):
            keys = set(HTML_TRANSLATION_PATTERN.findall(
                template.read_text(encoding="utf-8")
            ))
            keys.discard("{{ error_key }}")
            absent = keys - available_keys
            if absent:
                missing[template.name] = sorted(absent)

        self.assertEqual(missing, {})
