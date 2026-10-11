# contentdisp

Parse and build HTTP Content-Disposition headers, with correct RFC 5987 filename* handling

## Install

```
pip install contentdisp
```

## Usage

```python
from contentdisp import build, parse

# Parse a header, preferring the decoded RFC 5987 filename* over the plain fallback.
disposition = parse("attachment; filename=\"EURO rates.txt\"; filename*=UTF-8''%E2%82%AC%20rates.txt")
disposition.type        # "attachment"
disposition.filename    # "€ rates.txt"
disposition.params      # {"filename": "€ rates.txt"}

# Build a header. An ASCII name stays plain.
build("attachment", "report.pdf")
# 'attachment; filename="report.pdf"'

# A non-ASCII name emits an ASCII fallback plus a correct filename*.
build("attachment", "€ rates.txt")
# "attachment; filename=\"_ rates.txt\"; filename*=UTF-8''%E2%82%AC%20rates.txt"
```

Parsing is tolerant: a parameter without `=`, a malformed extended value, or an
unknown charset is kept as raw text rather than raising.

## Why

Clients get `filename*` wrong constantly: they skip the extended form, forget to
percent-decode it, ignore the declared charset, or emit a bare UTF-8 name with no
ASCII fallback. The existing options do not close the gap: `rfc6266` is years
without a release, and `content-disposition` only generates response headers for
Django and Django REST Framework. There was no small, typed, zero-dependency
library that both parses and builds the header with RFC 5987 handled correctly.
Reach for it whenever you read or write a Content-Disposition header and need the
extended name to round-trip.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
