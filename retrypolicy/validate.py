"""Semantic checks that run after parsing.

The parser only enforces grammar. A file can be syntactically fine and
still name a backoff strategy that doesn't exist, ask for zero or
negative attempts, or set jitter to a typo. This catches that class of
mistake with the same line/column precision as a parse error.
"""
from __future__ import annotations

from .errors import SourceError
from .formatter import Call, ListValue, PolicyNode, Scalar

KNOWN_BACKOFF_KINDS = ("constant", "linear", "exponential")
KNOWN_JITTER_KINDS = ("equal", "full", "none")


def validate_policies(policies: list, source: str, filename: str) -> None:
    for policy in policies:
        _validate_policy(policy, source, filename)


def _validate_policy(policy: PolicyNode, source: str, filename: str) -> None:
    for f in policy.fields:
        if f.key == "max_attempts":
            _validate_max_attempts(f, source, filename)
        elif f.key == "backoff":
            _validate_backoff(f, source, filename)
        elif f.key == "jitter":
            _validate_jitter(f, source, filename)


def _position(f):
    value = f.value
    if isinstance(value, (Scalar, Call)):
        return value.line, value.column
    return f.line, f.column


def _validate_max_attempts(f, source: str, filename: str) -> None:
    value = f.value
    if isinstance(value, Scalar) and value.kind == "number" and value.text.isdigit() and int(value.text) > 0:
        return
    line, column = _position(f)
    raise SourceError(
        source, filename, line, column,
        f"max_attempts must be a positive integer, got {_describe(value)}",
    )


def _validate_backoff(f, source: str, filename: str) -> None:
    value = f.value
    if isinstance(value, Call):
        if value.name in KNOWN_BACKOFF_KINDS:
            return
        raise SourceError(
            source, filename, value.line, value.column,
            f"unknown backoff kind {value.name!r} "
            f"(expected one of: {', '.join(KNOWN_BACKOFF_KINDS)})",
        )
    line, column = _position(f)
    raise SourceError(
        source, filename, line, column,
        f"backoff must be a call like exponential(...), got {_describe(value)}",
    )


def _validate_jitter(f, source: str, filename: str) -> None:
    value = f.value
    if isinstance(value, Scalar) and value.kind == "ident" and value.text in KNOWN_JITTER_KINDS:
        return
    line, column = _position(f)
    label = repr(value.text) if isinstance(value, Scalar) else _describe(value)
    raise SourceError(
        source, filename, line, column,
        f"unknown jitter kind {label} "
        f"(expected one of: {', '.join(KNOWN_JITTER_KINDS)})",
    )


def _describe(value) -> str:
    if isinstance(value, Scalar):
        return f"{value.kind} {value.text!r}"
    if isinstance(value, Call):
        return f"a call to {value.name!r}"
    if isinstance(value, ListValue):
        return "a list"
    return "an unrecognized value"
