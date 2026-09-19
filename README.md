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

## Testing

```
$ python -m unittest discover
```

covers the lexer (token boundaries, line/column tracking, comment
handling), the parser (value kinds, nested lists/calls, and where each
malformed-input error points), and end-to-end formatting.

## Status

Early skeleton. The lexer, parser, and canonical renderer work for the
grammar described above. Not yet handled: comments preservation and
field ordering/validation (e.g. catching unknown backoff strategies or
attempts <= 0).
