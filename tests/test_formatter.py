import unittest

from retrypolicy.errors import SourceError
from retrypolicy.formatter import format_source


class FormatSourceTests(unittest.TestCase):
    def test_canonicalizes_messy_input(self):
        messy = (
            "policy   checkout-service{\n"
            "max_attempts=5\n"
            "backoff=exponential(base=200MS,factor=2.0,max=10S)\n"
            "jitter=full\n"
            'retry_on=[502,503,"timeout"]\n'
            "}\n"
        )
        expected = (
            "policy checkout-service {\n"
            "  max_attempts = 5\n"
            "  backoff = exponential(base=200ms, factor=2.0, max=10s)\n"
            "  jitter = full\n"
            '  retry_on = [502, 503, "timeout"]\n'
            "}\n"
        )
        self.assertEqual(format_source(messy), expected)

    def test_already_canonical_input_is_unchanged(self):
        canonical = (
            "policy checkout-service {\n"
            "  max_attempts = 5\n"
            "  jitter = full\n"
            "}\n"
        )
        self.assertEqual(format_source(canonical), canonical)

    def test_empty_file_raises_at_start_of_file(self):
        with self.assertRaises(SourceError) as ctx:
            format_source("", filename="empty.rp")
        exc = ctx.exception
        self.assertEqual((exc.line, exc.column), (1, 1))
        self.assertEqual(exc.message, "file contains no policy blocks")

    def test_comment_only_file_raises_no_policy_blocks(self):
        with self.assertRaises(SourceError) as ctx:
            format_source("# nothing here\n", filename="empty.rp")
        self.assertEqual(ctx.exception.message, "file contains no policy blocks")


if __name__ == "__main__":
    unittest.main()
