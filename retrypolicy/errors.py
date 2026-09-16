"""Error types with source snippets.

The whole point of this tool is that when a policy file is malformed you
get told exactly where and why, not a bare "invalid syntax".
"""
from __future__ import annotations


class SourceError(Exception):
    def __init__(self, source: str, filename: str, line: int, column: int, message: str):
        self.source = source
        self.filename = filename
        self.line = line
        self.column = column
        self.message = message
        super().__init__(self.render())

    def render(self) -> str:
        lines = self.source.splitlines() or [""]
        index = self.line - 1
        line_text = lines[index] if 0 <= index < len(lines) else ""
        gutter = str(self.line)
        pad = " " * len(gutter)
        pointer = " " * (self.column - 1) + "^"
        return "\n".join([
            f"error: {self.message}",
            f"{pad}--> {self.filename}:{self.line}:{self.column}",
            f"{pad} |",
            f"{gutter} | {line_text}",
            f"{pad} | {pointer}",
        ])

    def __str__(self) -> str:
        return self.render()
