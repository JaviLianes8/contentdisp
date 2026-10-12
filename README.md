# contentdisp

Parse and build HTTP `Content-Disposition` headers per RFC 6266, with RFC 8187
`filename*` handled correctly and a `safe_filename` helper that turns the advisory name
into one you can write to disk.

Typed, no dependencies, Python 3.10+.

## Install

```
pip install contentdisp
```

## Read a download's file name

```python
from contentdisp import parse, safe_filename

header = "attachment; filename=\"EURO rates\"; filename*=utf-8''%e2%82%ac%20rates"
disposition = parse(header)
print(disposition.type)  # attachment
print(disposition.filename)  # € rates
print(disposition.is_attachment)  # True
```

`filename*` wins over `filename` when both are present (RFC 6266 section 4.3). Only
UTF-8 and ISO-8859-1 extended values are decoded; one that is malformed or in another
charset is ignored, so the plain `filename` is used instead.

## Never trust the name

The file name comes from the server and is advisory. `safe_filename` keeps only the last
path segment, removes control and invisible format characters (text-direction controls,
zero-width spaces), replaces characters Windows refuses, neutralises device names such as
`CON`, strips leading dots and caps the length at 255 UTF-8 bytes, keeping the extension.
The `default` is returned as given when nothing usable is left:

```python
from contentdisp import parse, safe_filename

print(safe_filename("../../etc/passwd"))  # passwd
print(safe_filename(parse("attachment; filename*=UTF-8''%5cfoo.html").filename))  # foo.html
print(safe_filename("CON.txt"))  # _CON.txt
print(safe_filename(".htaccess"))  # htaccess
print(safe_filename(parse("inline").filename, default="page.html"))  # page.html
```

## Lenient or strict

By default `parse` never raises `ValueError`: it reads what it can, the way browsers do,
and returns the same result as the strict mode on every valid header. Pass `strict=True`
to reject anything outside the grammar, a repeated parameter or an undecodable
`filename*`:

```python
from contentdisp import parse

print(parse("attachment; filename=a; filename=b").filename)  # a
try:
    parse("attachment; filename=a; filename=b", strict=True)
except ValueError as error:
    print(error)  # parameter 'filename' appears more than once
```

Raw header bytes (as ASGI servers hand them over) are decoded as ISO-8859-1.

## Build a header

```python
from contentdisp import build

print(build("attachment", "report.pdf"))  # attachment; filename="report.pdf"
print(build("attachment", "€.txt"))  # attachment; filename="_.txt"; filename*=UTF-8''%E2%82%AC.txt
print(build("form-data", "résumé.pdf", name="cv"))  # form-data; filename="résumé.pdf"; name="cv"
```

When the plain `filename` cannot carry the name exactly (non-ASCII, `\`, `"` or a `%41`
style sequence, all things RFC 6266 Appendix D says to avoid there), `build` writes an
ASCII fallback first and the exact name as UTF-8 `filename*`. Accented letters fall back
to their base letter. For `form-data` no `filename*` is written, as RFC 7578 section 4.2
requires: the name stays UTF-8, CR, LF and `"` are percent-escaped as browsers do, and so
is a backslash, which would otherwise swallow the next parameter. Control characters, a
type or parameter name that is not a token, and a parameter given twice raise
`ValueError`, so a header can never be split.

A multipart part header is UTF-8: decode it yourself and pass `str` to `parse`, whose
strict mode accepts any non-ASCII character inside a quoted-string.

## API

| Name | What it does |
| --- | --- |
| `parse(header, *, strict=False)` | `str` or `bytes` to `ContentDisposition`. |
| `ContentDisposition` | Frozen value: `type`, `params`, `filename`, `is_attachment`. |
| `build(type, filename=None, **params)` | Header value; keyword `_` becomes `-`. |
| `safe_filename(name, *, default="download", max_bytes=255)` | Harmless file name. |

Not supported on purpose: RFC 2231 continuations (`filename*0`, `filename*1`), RFC 2047
encoded words and percent-decoding of the plain `filename`. RFC 6266 does not adopt them
and the browser test corpus checks that the last two are not applied.

## Why

Clients get `filename*` wrong constantly: they skip the extended form, forget to
percent-decode it, ignore the declared charset, or let a broken one replace a good
fallback. Servers emit bare UTF-8 names, or let a newline from user input split the
header. And almost nobody strips the path from the name before saving. `rfc6266` has
been without a release for years, and `content-disposition` only generates response
headers for Django. This library parses and builds the header, is checked against the
RFC examples and every case of the browser test corpus, and makes the safe name the easy
one to use.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
