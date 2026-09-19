import unittest

from retrypolicy.errors import SourceError


class SourceErrorRenderTests(unittest.TestCase):
    def test_render_points_at_line_and_column(self):
        source = "abc\ndefgh\n"
        exc = SourceError(source, "<input>", 2, 3, "test message")
        rendered = str(exc)
        self.assertEqual(
            rendered,
            "\n".join(
                [
                    "error: test message",
                    " --> <input>:2:3",
                    "  |",
                    "2 | defgh",
                    "  |   ^",
                ]
            ),
        )

    def test_carets_up_with_offending_character(self):
        # a parser-style error: the caret should sit under the character
        # that made this position wrong, not just somewhere on the line.
        source = "  a 5\n"
        exc = SourceError(source, "<input>", 1, 5, "expected '='")
        lines = str(exc).splitlines()
        content_line, pointer_line = lines[-2], lines[-1]
        caret_offset = pointer_line.index("^") - content_line.index("| ") - 2
        self.assertEqual(source.splitlines()[0][caret_offset], "5")


if __name__ == "__main__":
    unittest.main()
