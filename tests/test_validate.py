import unittest

from retrypolicy.errors import SourceError
from retrypolicy.formatter import format_source


class MaxAttemptsValidationTests(unittest.TestCase):
    def test_zero_attempts_rejected(self):
        source = "policy p {\n  max_attempts = 0\n}\n"
        with self.assertRaises(SourceError) as ctx:
            format_source(source)
        exc = ctx.exception
        self.assertEqual((exc.line, exc.column), (2, 18))
        self.assertEqual(
            exc.message,
            "max_attempts must be a positive integer, got number '0'",
        )

    def test_negative_attempts_rejected(self):
        source = "policy p {\n  max_attempts = -3\n}\n"
        with self.assertRaises(SourceError):
            format_source(source)

    def test_non_integer_attempts_rejected(self):
        source = "policy p {\n  max_attempts = 5ms\n}\n"
        with self.assertRaises(SourceError) as ctx:
            format_source(source)
        self.assertIn("max_attempts must be a positive integer", ctx.exception.message)

    def test_positive_attempts_accepted(self):
        source = "policy p {\n  max_attempts = 5\n}\n"
        format_source(source)  # no error


class BackoffValidationTests(unittest.TestCase):
    def test_unknown_backoff_kind_rejected(self):
        source = "policy p {\n  backoff = fibonacci(base=1)\n}\n"
        with self.assertRaises(SourceError) as ctx:
            format_source(source)
        exc = ctx.exception
        self.assertEqual((exc.line, exc.column), (2, 13))
        self.assertEqual(
            exc.message,
            "unknown backoff kind 'fibonacci' "
            "(expected one of: constant, linear, exponential)",
        )

    def test_backoff_must_be_a_call(self):
        source = "policy p {\n  backoff = full\n}\n"
        with self.assertRaises(SourceError) as ctx:
            format_source(source)
        self.assertIn("backoff must be a call like exponential(...)", ctx.exception.message)

    def test_known_backoff_kinds_accepted(self):
        for kind in ("constant", "linear", "exponential"):
            source = f"policy p {{\n  backoff = {kind}(base=1)\n}}\n"
            format_source(source)  # no error


class JitterValidationTests(unittest.TestCase):
    def test_unknown_jitter_kind_rejected(self):
        source = "policy p {\n  jitter = maybe\n}\n"
        with self.assertRaises(SourceError) as ctx:
            format_source(source)
        exc = ctx.exception
        self.assertEqual((exc.line, exc.column), (2, 12))
        self.assertEqual(
            exc.message,
            "unknown jitter kind 'maybe' (expected one of: equal, full, none)",
        )

    def test_known_jitter_kinds_accepted(self):
        for kind in ("equal", "full", "none"):
            source = f"policy p {{\n  jitter = {kind}\n}}\n"
            format_source(source)  # no error


if __name__ == "__main__":
    unittest.main()
