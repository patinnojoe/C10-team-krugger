import json
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from tokenizer import Tokenizer


class TokenizerTests(unittest.TestCase):
    def test_fresh_instance_roundtrip_and_types(self):
        texts = [
            "", " ", "hello", "hello world", "multiple   spaces",
            "  leading", "trailing  ", "punctuation!? 123", "a" * 1000,
            "prefix pre pref", "line one\nline\ttwo",
            "[U+00E9 LATIN SMALL LETTER E WITH ACUTE]",
            "".join(chr(i) for i in range(128)),
        ]
        encoded = Tokenizer().encode(texts)
        self.assertEqual(Tokenizer().decode(encoded), texts)
        self.assertTrue(all(type(value) is int for row in encoded for value in row))

    def test_invalid_id(self):
        with self.assertRaises(ValueError):
            Tokenizer().decode([[999999999]])

    def test_vocab_limit(self):
        model = json.loads((PROJECT_ROOT / "tokenizer.json").read_text(encoding="utf-8"))
        self.assertLessEqual(len(model["tokens"]), 20_000)


if __name__ == "__main__":
    unittest.main()
