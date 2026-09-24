"""Parsing and normalization for the retry-policy config language.

A policy file looks like this:

    policy checkout-service {
      max_attempts = 5
      backoff = exponential(base=200ms, factor=2.0, max=10s)
      jitter = full
      retry_on = [502, 503, "timeout"]
    }

format_source() re-parses that into a small AST and re-renders it in a
single canonical layout: two-space indent, one field per line, double
quotes, lower-cased units. Anything that doesn't parse raises a
SourceError pointing at the exact line and column.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .errors import SourceError

KEYWORDS = {"policy"}

_SYMBOLS = {
    "{": "LBRACE",
    "}": "RBRACE",
    "(": "LPAREN",
    ")": "RPAREN",
    "[": "LBRACKET",
    "]": "RBRACKET",
    "=": "EQUALS",
    ",": "COMMA",
}


@dataclass(frozen=True)
class Token:
    type: str
    value: str
    line: int
    column: int


def tokenize(source: str, filename: str) -> list:
    tokens = []
    line = col = 1
    i, n = 0, len(source)

    def advance(count: int = 1) -> None:
        nonlocal i, line, col
        for _ in range(count):
            if source[i] == "\n":
                line += 1
                col = 1
            else:
                col += 1
            i += 1

    while i < n:
        ch = source[i]

        if ch.isspace():
            advance()
            continue

        if ch == "#":
            while i < n and source[i] != "\n":
                advance()
            continue

        start_line, start_col = line, col

        if ch in _SYMBOLS:
            tokens.append(Token(_SYMBOLS[ch], ch, start_line, start_col))
            advance()
            continue

        if ch == '"':
            advance()
            chars = []
            while i < n and source[i] != '"' and source[i] != "\n":
                chars.append(source[i])
                advance()
            if i >= n or source[i] == "\n":
                raise SourceError(source, filename, start_line, start_col, "unterminated string literal")
            advance()  # closing quote
            tokens.append(Token("STRING", "".join(chars), start_line, start_col))
            continue

        if ch.isdigit() or (ch == "-" and i + 1 < n and source[i + 1].isdigit()):
            j = i + 1 if ch == "-" else i
            while j < n and (source[j].isdigit() or source[j] == "."):
                j += 1
            while j < n and source[j].isalpha():
                j += 1
            tokens.append(Token("NUMBER", source[i:j], start_line, start_col))
            advance(j - i)
            continue

        if ch.isalpha() or ch == "_":
            j = i
            while j < n and (source[j].isalnum() or source[j] in "_-"):
                j += 1
            word = source[i:j]
            tokens.append(Token("KEYWORD" if word in KEYWORDS else "IDENT", word, start_line, start_col))
            advance(j - i)
            continue

        raise SourceError(source, filename, start_line, start_col, f"unexpected character {ch!r}")

    tokens.append(Token("EOF", "", line, col))
    return tokens


@dataclass
class Scalar:
    kind: str  # "number", "string", "ident"
    text: str
    # position is informational only (used by validation error messages),
    # so it's excluded from equality to keep the existing positive tests
    # working without threading line/column through every fixture.
    line: int = field(default=0, compare=False)
    column: int = field(default=0, compare=False)


@dataclass
class ListValue:
    items: list


@dataclass
class Call:
    name: str
    args: list  # list[tuple[str, Scalar]]
    line: int = field(default=0, compare=False)
    column: int = field(default=0, compare=False)


@dataclass
class FieldNode:
    key: str
    value: object
    line: int = 0
    column: int = 0


@dataclass
class PolicyNode:
    name: str
    fields: list = field(default_factory=list)


class Parser:
    def __init__(self, source: str, filename: str):
        self.source = source
        self.filename = filename
        self.tokens = tokenize(source, filename)
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos]

    def advance(self):
        tok = self.tokens[self.pos]
        if tok.type != "EOF":
            self.pos += 1
        return tok

    def expect(self, type_: str, hint: str):
        tok = self.peek()
        if tok.type != type_:
            raise SourceError(self.source, self.filename, tok.line, tok.column, hint)
        return self.advance()

    def parse_file(self) -> list:
        policies = []
        while self.peek().type != "EOF":
            policies.append(self.parse_policy())
        return policies

    def parse_policy(self) -> PolicyNode:
        tok = self.peek()
        if tok.type != "KEYWORD" or tok.value != "policy":
            raise SourceError(
                self.source, self.filename, tok.line, tok.column,
                f"expected a policy block, found {tok.value or 'end of file'!r}",
            )
        self.advance()
        name_tok = self.expect("IDENT", "expected a policy name after 'policy'")
        self.expect("LBRACE", f"expected '{{' after policy name {name_tok.value!r}")
        policy = PolicyNode(name=name_tok.value)
        while self.peek().type != "RBRACE":
            if self.peek().type == "EOF":
                raise SourceError(
                    self.source, self.filename, name_tok.line, name_tok.column,
                    f"policy {name_tok.value!r} is missing a closing '}}'",
                )
            policy.fields.append(self.parse_field())
        self.advance()  # RBRACE
        return policy

    def parse_field(self) -> FieldNode:
        key_tok = self.expect("IDENT", "expected a field name")
        self.expect("EQUALS", f"expected '=' after key {key_tok.value!r}")
        value = self.parse_value()
        return FieldNode(key=key_tok.value, value=value, line=key_tok.line, column=key_tok.column)

    def parse_value(self):
        tok = self.peek()
        if tok.type == "LBRACKET":
            return self.parse_list()
        if tok.type == "IDENT" and self.tokens[self.pos + 1].type == "LPAREN":
            return self.parse_call()
        if tok.type in ("NUMBER", "STRING", "IDENT"):
            return self.parse_scalar()
        raise SourceError(
            self.source, self.filename, tok.line, tok.column,
            f"expected a value, found {tok.value or 'end of file'!r}",
        )

    def parse_scalar(self) -> Scalar:
        tok = self.advance()
        kind = {"NUMBER": "number", "STRING": "string", "IDENT": "ident"}[tok.type]
        return Scalar(kind=kind, text=tok.value, line=tok.line, column=tok.column)

    def parse_list(self) -> ListValue:
        self.advance()  # LBRACKET
        items = []
        if self.peek().type != "RBRACKET":
            items.append(self.parse_scalar())
            while self.peek().type == "COMMA":
                self.advance()
                items.append(self.parse_scalar())
        self.expect("RBRACKET", "expected ']' to close this list")
        return ListValue(items=items)

    def parse_call(self) -> Call:
        name_tok = self.advance()  # IDENT
        self.advance()  # LPAREN
        args = []
        if self.peek().type != "RPAREN":
            args.append(self.parse_arg())
            while self.peek().type == "COMMA":
                self.advance()
                args.append(self.parse_arg())
        self.expect("RPAREN", f"expected ')' to close {name_tok.value!r}")
        return Call(name=name_tok.value, args=args, line=name_tok.line, column=name_tok.column)

    def parse_arg(self):
        key_tok = self.expect("IDENT", "expected an argument name")
        self.expect("EQUALS", f"expected '=' after argument {key_tok.value!r}")
        value = self.parse_scalar()
        return (key_tok.value, value)


def _render_scalar(scalar: Scalar) -> str:
    if scalar.kind == "string":
        return f'"{scalar.text}"'
    if scalar.kind == "number":
        return scalar.text.lower()
    return scalar.text


def _render_value(value) -> str:
    if isinstance(value, ListValue):
        return "[" + ", ".join(_render_scalar(item) for item in value.items) + "]"
    if isinstance(value, Call):
        args = ", ".join(f"{k}={_render_scalar(v)}" for k, v in value.args)
        return f"{value.name}({args})"
    return _render_scalar(value)


def render(policies: list) -> str:
    blocks = []
    for policy in policies:
        lines = [f"policy {policy.name} {{"]
        for f_ in policy.fields:
            lines.append(f"  {f_.key} = {_render_value(f_.value)}")
        lines.append("}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"


def format_source(source: str, filename: str = "<input>") -> str:
    parser = Parser(source, filename)
    policies = parser.parse_file()
    if not policies:
        first = parser.tokens[0]
        raise SourceError(source, filename, first.line, first.column, "file contains no policy blocks")

    from .validate import validate_policies  # deferred: validate imports these node types

    validate_policies(policies, source, filename)
    return render(policies)
