import unittest

from retrypolicy.errors import SourceError
from retrypolicy.formatter import tokenize


class TokenizeTests(unittest.TestCase):
    def test_symbols_and_keyword(self):
        tokens = tokenize("policy a {\n}\n", "<input>")
        kinds = [(t.type, t.value, t.line, t.column) for t in tokens]
        self.assertEqual(
            kinds,
            [
                ("KEYWORD", "policy", 1, 1),
                ("IDENT", "a", 1, 8),
                ("LBRACE", "{", 1, 10),
                ("RBRACE", "}", 2, 1),
                ("EOF", "", 3, 1),
            ],
        )

    def test_number_with_unit_suffix(self):
        tokens = tokenize("200ms", "<input>")
        self.assertEqual(tokens[0].type, "NUMBER")
        self.assertEqual(tokens[0].value, "200ms")
        self.assertEqual((tokens[0].line, tokens[0].column), (1, 1))

    def test_negative_decimal_with_suffix(self):
        tokens = tokenize("-3.5x", "<input>")
        self.assertEqual(tokens[0].type, "NUMBER")
        self.assertEqual(tokens[0].value, "-3.5x")

    def test_string_literal(self):
        tokens = tokenize('"timeout"', "<input>")
        self.assertEqual(tokens[0].type, "STRING")
        self.assertEqual(tokens[0].value, "timeout")
        self.assertEqual((tokens[0].line, tokens[0].column), (1, 1))

    def test_comment_is_skipped_and_line_tracking_continues(self):
        tokens = tokenize("# a comment\npolicy\n", "<input>")
        self.assertEqual(tokens[0].type, "KEYWORD")
        self.assertEqual(tokens[0].value, "policy")
        self.assertEqual((tokens[0].line, tokens[0].column), (2, 1))

    def test_identifier_allows_hyphen(self):
        tokens = tokenize("checkout-service", "<input>")
        self.assertEqual(tokens[0].type, "IDENT")
        self.assertEqual(tokens[0].value, "checkout-service")

    def test_unexpected_character_raises_source_error(self):
        with self.assertRaises(SourceError) as ctx:
            tokenize("@", "<input>")
        exc = ctx.exception
        self.assertEqual((exc.line, exc.column), (1, 1))
        self.assertIn("unexpected character", exc.message)

    def test_unterminated_string_raises_at_opening_quote(self):
        with self.assertRaises(SourceError) as ctx:
            tokenize('"ab\ncd"', "<input>")
        exc = ctx.exception
        self.assertEqual((exc.line, exc.column), (1, 1))
        self.assertIn("unterminated string literal", exc.message)


if __name__ == "__main__":
    unittest.main()
