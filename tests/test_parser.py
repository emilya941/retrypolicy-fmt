import unittest

from retrypolicy.errors import SourceError
from retrypolicy.formatter import Call, ListValue, Parser, Scalar


def parse(source, filename="<input>"):
    return Parser(source, filename).parse_file()


class ParserPositiveTests(unittest.TestCase):
    def test_parses_scalar_kinds(self):
        source = (
            "policy svc {\n"
            "  a = 1\n"
            '  b = "x"\n'
            "  c = ident\n"
            "}\n"
        )
        policies = parse(source)
        self.assertEqual(len(policies), 1)
        fields = {f.key: f.value for f in policies[0].fields}
        self.assertEqual(fields["a"], Scalar(kind="number", text="1"))
        self.assertEqual(fields["b"], Scalar(kind="string", text="x"))
        self.assertEqual(fields["c"], Scalar(kind="ident", text="ident"))

    def test_parses_list(self):
        source = "policy svc {\n  d = [1, 2, 3]\n}\n"
        policies = parse(source)
        value = policies[0].fields[0].value
        self.assertIsInstance(value, ListValue)
        self.assertEqual(
            value.items,
            [
                Scalar(kind="number", text="1"),
                Scalar(kind="number", text="2"),
                Scalar(kind="number", text="3"),
            ],
        )

    def test_parses_call_with_keyword_args(self):
        source = "policy svc {\n  backoff = exponential(base=200ms, factor=2.0)\n}\n"
        policies = parse(source)
        value = policies[0].fields[0].value
        self.assertIsInstance(value, Call)
        self.assertEqual(value.name, "exponential")
        self.assertEqual(
            value.args,
            [
                ("base", Scalar(kind="number", text="200ms")),
                ("factor", Scalar(kind="number", text="2.0")),
            ],
        )

    def test_parses_multiple_policies(self):
        source = "policy a {\n  x = 1\n}\n\npolicy b {\n  y = 2\n}\n"
        policies = parse(source)
        self.assertEqual([p.name for p in policies], ["a", "b"])
        self.assertEqual(policies[0].fields[0].key, "x")
        self.assertEqual(policies[1].fields[0].key, "y")


class ParserCommentTests(unittest.TestCase):
    def test_leading_comment_above_policy(self):
        source = "# about svc\npolicy svc {\n  x = 1\n}\n"
        policies = parse(source)
        self.assertEqual(policies[0].leading_comments, ["about svc"])

    def test_leading_comment_above_field(self):
        source = "policy svc {\n  # why 1\n  x = 1\n}\n"
        policies = parse(source)
        self.assertEqual(policies[0].fields[0].leading_comments, ["why 1"])

    def test_multiple_leading_comment_lines_are_kept_in_order(self):
        source = "policy svc {\n  # first\n  # second\n  x = 1\n}\n"
        field = parse(source)[0].fields[0]
        self.assertEqual(field.leading_comments, ["first", "second"])

    def test_trailing_comment_on_field_line(self):
        source = "policy svc {\n  x = 1  # note\n}\n"
        field = parse(source)[0].fields[0]
        self.assertEqual(field.trailing_comment, "note")
        self.assertEqual(field.leading_comments, [])

    def test_comment_on_its_own_line_is_not_treated_as_trailing(self):
        source = "policy svc {\n  x = 1\n  # not attached to x\n  y = 2\n}\n"
        fields = parse(source)[0].fields
        self.assertIsNone(fields[0].trailing_comment)
        self.assertEqual(fields[1].leading_comments, ["not attached to x"])

    def test_dangling_comment_before_closing_brace(self):
        source = "policy svc {\n  x = 1\n  # trailing note\n}\n"
        policy = parse(source)[0]
        self.assertEqual(policy.trailing_comments, ["trailing note"])

    def test_comment_after_last_policy_is_kept_as_file_trailing(self):
        source = "policy svc {\n  x = 1\n}\n# end of file\n"
        parser = Parser(source, "<input>")
        parser.parse_file()
        self.assertEqual(parser.trailing_comments, ["end of file"])


class ParserErrorPositionTests(unittest.TestCase):
    def test_missing_equals_after_key(self):
        source = "policy p {\n  a 5\n}\n"
        with self.assertRaises(SourceError) as ctx:
            parse(source)
        exc = ctx.exception
        self.assertEqual((exc.line, exc.column), (2, 5))
        self.assertEqual(exc.message, "expected '=' after key 'a'")

    def test_missing_policy_name(self):
        source = "policy {\n}\n"
        with self.assertRaises(SourceError) as ctx:
            parse(source)
        exc = ctx.exception
        self.assertEqual((exc.line, exc.column), (1, 8))
        self.assertEqual(exc.message, "expected a policy name after 'policy'")

    def test_missing_closing_brace(self):
        source = "policy p {\n  a = 1\n"
        with self.assertRaises(SourceError) as ctx:
            parse(source)
        exc = ctx.exception
        self.assertEqual((exc.line, exc.column), (1, 8))
        self.assertEqual(exc.message, "policy 'p' is missing a closing '}'")

    def test_list_missing_closing_bracket(self):
        source = "policy p {\n  a = [1, 2\n}\n"
        with self.assertRaises(SourceError) as ctx:
            parse(source)
        exc = ctx.exception
        self.assertEqual((exc.line, exc.column), (3, 1))
        self.assertEqual(exc.message, "expected ']' to close this list")

    def test_call_missing_closing_paren(self):
        source = "policy p {\n  a = fn(x=1\n}\n"
        with self.assertRaises(SourceError) as ctx:
            parse(source)
        exc = ctx.exception
        self.assertEqual((exc.line, exc.column), (3, 1))
        self.assertEqual(exc.message, "expected ')' to close 'fn'")


if __name__ == "__main__":
    unittest.main()
