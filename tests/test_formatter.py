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


class CommentPreservationTests(unittest.TestCase):
    def test_preserves_leading_and_trailing_comments(self):
        messy = (
            "# checkout retries\n"
            "policy checkout-service {\n"
            "  # tuned after the 2026-08 incident\n"
            "  max_attempts = 5\n"
            "  jitter = full  # avoid thundering herd\n"
            "  # not wired up yet\n"
            "}\n"
        )
        expected = (
            "# checkout retries\n"
            "policy checkout-service {\n"
            "  # tuned after the 2026-08 incident\n"
            "  max_attempts = 5\n"
            "  jitter = full  # avoid thundering herd\n"
            "  # not wired up yet\n"
            "}\n"
        )
        self.assertEqual(format_source(messy), expected)

    def test_preserves_comment_after_last_policy(self):
        source = "policy a {\n  x = 1\n}\n# left here for reference\n"
        self.assertEqual(format_source(source), source)

    def test_formatting_is_idempotent_with_comments(self):
        source = (
            "policy a {\n"
            "  # note\n"
            "  x = 1  # inline\n"
            "}\n"
        )
        once = format_source(source)
        self.assertEqual(format_source(once), once)


if __name__ == "__main__":
    unittest.main()
