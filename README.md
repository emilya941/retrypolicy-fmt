# retrypolicy-fmt

A formatter for retry-policy config files.

Every service ends up with its own file describing how it retries failed
calls: max attempts, backoff strategy, jitter, which status codes are
retryable. In practice these files get hand-edited by whoever is on call,
so they drift: inconsistent spacing, mixed quote styles, `200MS` next to
`10s`, keys crammed onto one line. None of that is wrong, exactly, it's
just inconsistent enough that diffs are noisy and code review wastes time
on formatting instead of the actual retry behavior.

`retrypolicy-fmt` parses the file and re-prints it in one canonical style.
If the file doesn't parse, it tells you exactly where, with line and
column numbers, instead of a bare "invalid syntax".

## The file format

```
policy checkout-service {
  max_attempts = 5
  backoff = exponential(base=200ms, factor=2.0, max=10s)
  jitter = full
  retry_on = [502, 503, "timeout"]
}
```

A file is a list of `policy <name> { ... }` blocks. Each field is
`key = value`, where a value is a number (optionally with a unit suffix
like `ms`, `s`, `x`), a string, a bare identifier, a `[...]` list of
scalars, or a call like `exponential(base=200ms, factor=2.0)`.

## Usage

```
$ python -m retrypolicy.cli policy.rp
```

prints the normalized file to stdout. Add `--write` to rewrite the file
in place.

Given this messy input:

```
policy   checkout-service{
max_attempts=5
backoff=exponential(base=200MS,factor=2.0,max=10S)
jitter=full
retry_on=[502,503,"timeout"]
}
```

it produces:

```
policy checkout-service {
  max_attempts = 5
  backoff = exponential(base=200ms, factor=2.0, max=10s)
  jitter = full
  retry_on = [502, 503, "timeout"]
}
```

## Comments

`#` starts a comment that runs to the end of the line. A comment on its
own line above a `policy` block or a field is kept above that block or
field. A comment at the end of a field's line is kept on that line.
Comments right before a block's closing `}`, and any comment left after
the last policy in the file, are kept too.

```
# checkout retries
policy checkout-service {
  # tuned after the 2026-08 incident
  max_attempts = 5
  jitter = full  # avoid thundering herd
}
```

reformats unchanged. A comment in the middle of a value, such as inside
a `[...]` list or a call's argument list, is not preserved.

## Error messages

A missing `=`:

```
policy checkout-service {
  max_attempts 5
}
```

produces:

```
error: expected '=' after key 'max_attempts'
  --> policy.rp:2:16
  |
2 |   max_attempts 5
  |                ^
```

## Library use

```python
from retrypolicy import format_source, SourceError

try:
    print(format_source(open("policy.rp").read(), filename="policy.rp"))
except SourceError as exc:
    print(exc)  # already formatted with line/column and a source snippet
```

## Semantic validation

Parsing only checks grammar. A few fields are also checked for sense,
with errors pointing at the offending value the same way parse errors
do:

- `max_attempts` must be a positive integer.
- `backoff` must be a call to one of `constant`, `linear`, `exponential`.
- `jitter` must be one of `none`, `equal`, `full`.

```
policy checkout-service {
  backoff = fibonacci(base=1)
}
```

```
error: unknown backoff kind 'fibonacci' (expected one of: constant, linear, exponential)
  --> policy.rp:2:13
  |
2 |   backoff = fibonacci(base=1)
  |             ^
```

## Testing

```
$ python -m unittest discover
```

covers the lexer (token boundaries, line/column tracking, comment
handling), the parser (value kinds, nested lists/calls, comment
attachment, and where each malformed-input error points), semantic
validation, and end-to-end formatting.

## Status

Early skeleton. The lexer, parser, canonical renderer, field
validation, and comment preservation work for the grammar described
above. Not yet handled: a `--check` mode, multi-file/glob support on
the CLI, and precisely defined units and ranges (ms/s bounds, jitter
kinds beyond the name check).
