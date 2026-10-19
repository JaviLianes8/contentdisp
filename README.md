# contentdisp

[![Lianes8 Certified](https://lianes8studio.com/certified/lianes8-certified-badge.svg)](https://lianes8studio.com/certified)

Parse and build HTTP `Content-Disposition` headers per RFC 6266 and RFC 8187, and turn
the file name a server offers into one that is safe to write to disk.

Typed, no dependencies, Python 3.10+.

## Install

```
pip install contentdisp
```

## Usage

```python
from contentdisp import parse, safe_filename

# Read the file name a server offers: filename* wins over the plain fallback.
disposition = parse("attachment; filename=\"EURO rates\"; filename*=utf-8''%e2%82%ac%20rates")
print(disposition.type, disposition.filename, disposition.is_attachment)
# attachment € rates True

# Never trust it: keep a single harmless name.
print(safe_filename("../../etc/passwd"), safe_filename("CON.txt"), safe_filename(None))
# passwd _CON.txt download
```

### Building a header

```python
from contentdisp import build

print(build("attachment", "report.pdf"))
# attachment; filename="report.pdf"

# A name the plain form cannot carry gets an ASCII fallback and an exact filename*.
print(build("attachment", "€ rates.pdf"))
# attachment; filename="_ rates.pdf"; filename*=UTF-8''%E2%82%AC%20rates.pdf

# form-data never uses filename* (RFC 7578): the name stays UTF-8.
print(build("form-data", "résumé.pdf", name="cv"))
# form-data; filename="résumé.pdf"; name="cv"
```

### Lenient or strict

```python
from contentdisp import ContentDispositionError, parse

# Default: read what can be read, as browsers do; the first of a repeated parameter wins.
print(parse("attachment; filename=a.txt; filename=b.txt").filename)
# a.txt

# strict=True: the grammar exactly, with the position of the first offending character.
try:
    parse("attachment; filename=a.txt; filename=b.txt", strict=True)
except ContentDispositionError as error:
    print(error.position)
# 28
```

## API

| Name | What it does |
| --- | --- |
| `parse(header, *, strict=False)` | `str` or `bytes` (read as ISO-8859-1) to a `ContentDisposition`. |
| `ContentDisposition` | Frozen value: `type`, `params`, `filename` (prefers `filename*`), `is_attachment`. |
| `build(type, /, filename=None, **params)` | Header value that cannot be split; keyword `_` becomes `-`; a `ContentDisposition` as `type` is written with its names as they are. |
| `safe_filename(name, *, default="download", max_bytes=255)` | A single harmless file name, or `default`. |
| `ContentDispositionError` | `ValueError` subclass with `position` (or `None`). Wrong argument types raise `TypeError`. |

## Rules it follows

Strict mode is the RFC 6266 grammar exactly, with token and quoted-string as RFC 9110
defines them and `filename*` as RFC 8187 does, language tags included. The default mode
gives the same result on every valid header and recovers what it can from the others,
as RFC 6266 section 3 allows. Building follows the advice of RFC 6266 Appendix D, and
`safe_filename` the security rules of its section 4.3. The
[GUIDE](https://github.com/JaviLianes8/contentdisp/blob/main/GUIDE.md) has every rule in
detail, and the [CHANGELOG](https://github.com/JaviLianes8/contentdisp/blob/main/CHANGELOG.md)
what changed in each release.

## Why

Reading this header right is easy to get wrong, and the Python tools around get it
wrong in different ways. `werkzeug.http.parse_options_header` (werkzeug 3.1.9) lets
whichever of `filename` and `filename*` comes last win, and returns no file name at all
for `INLINE; FILENAME= "an example.html"`, an example from RFC 6266 itself. Python's
`email` package keeps whichever comes first, so it reads the ASCII fallback of a header
written the way RFC 6266 advises, and `multipart` 2.0.1 ignores `filename*`. `aiohttp`
picks `filename*` in either order, inside a whole HTTP framework. `rfc6266`, the package named after the
RFC, has had no release since 2013 and no longer builds with current setuptools. And for
saving the file, `werkzeug.utils.secure_filename("東京.txt")` returns `"txt"`.

`contentdisp` is small, typed and dependency-free: it parses strictly or leniently,
builds headers that cannot be split, and makes the safe file name the easy one. It is
tested against the specifications themselves, the browser test corpus RFC 6266 points
to, Chromium's own expectations, the jshttp parsers that Express uses, Microsoft's file
naming rules and Windows itself.

## Development

`python scripts/fetch_upstream.py` downloads the specifications and test data listed in
`tests/upstream/MANIFEST.json` (they are not part of the repository; their tests skip
without them). `pip install werkzeug aiohttp multipart` and Node.js add the reference
parsers. `scripts/check.ps1` runs format, lint, types and tests. Set `CONTENTDISP_E2E=1`
to also build the wheel and test the installed package.

## License

MIT. See [LICENSE](https://github.com/JaviLianes8/contentdisp/blob/main/LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
