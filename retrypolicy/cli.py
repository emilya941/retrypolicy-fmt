"""Command-line entry point: retrypolicy-fmt <file> [--write]"""
from __future__ import annotations

import sys

from .errors import SourceError
from .formatter import format_source


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("usage: retrypolicy-fmt <file> [--write]", file=sys.stderr)
        return 2

    write = "--write" in argv
    paths = [a for a in argv if a != "--write"]
    if len(paths) != 1:
        print("usage: retrypolicy-fmt <file> [--write]", file=sys.stderr)
        return 2

    path = paths[0]
    try:
        with open(path, "r", encoding="utf-8") as fh:
            source = fh.read()
    except OSError as exc:
        print(f"error: cannot read {path}: {exc}", file=sys.stderr)
        return 1

    try:
        formatted = format_source(source, filename=path)
    except SourceError as exc:
        print(exc, file=sys.stderr)
        return 1

    if write:
        if formatted != source:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(formatted)
    else:
        sys.stdout.write(formatted)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
