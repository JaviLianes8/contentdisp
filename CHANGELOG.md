# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-19

The public API is now stable: the five names in `contentdisp.__all__`, their signatures,
defaults and error types follow Semantic Versioning from this release on.

### Stable

- `parse` reads a header strictly (`strict=True`, the RFC 6266 grammar with RFC 9110,
  RFC 8187 and RFC 5646 rules) or leniently (the default: the same result on every valid
  header, recovery on the others), and returns a `ContentDisposition`.
- `ContentDisposition` with `type`, `params`, `filename` and `is_attachment`.
- `build` writes a header that cannot be split, following RFC 6266 Appendix D, and
  RFC 7578 for `form-data`; given a `ContentDisposition`, it writes that value again.
- `safe_filename` reduces an advisory name to one safe to create in a folder.
- `ContentDispositionError` (a `ValueError`) for invalid values, with the `position` of
  the first offending character for strict parsing; `TypeError` for arguments of the
  wrong type.

### Changed

- `build` takes its type positional only, so `type` can be a keyword parameter
  (`build("attachment", type="x")` raised `TypeError`; `build(type="attachment")` now
  does). It also takes a `ContentDisposition` in place of the type and writes its
  parameters with their names as they are, so a parsed header is written again with
  `build(parse(header))`, names with `_` included (keywords still turn `_` into `-`).
- A parameter named `*` alone is an ordinary parameter, as RFC 6266 defines an extended
  name as a token followed by `*`: `attachment; *=foo` gives `{'*': 'foo'}` in both modes
  (strict parsing refused it, lenient parsing dropped it, and `*=UTF-8''x` was stored
  under the empty name), and `build` writes it. `**` is its extended form.
- `build` reports a lone surrogate as `a lone surrogate`, no longer as a control
  character.
- `safe_filename` cuts a run of more than 30 combining marks to 30 before normalising, as
  the Unicode Stream-Safe Text Format does.
- Every `ValueError` the library raises is now a `ContentDispositionError`, a subclass,
  so `except ValueError` keeps working.
- Strict parsing checks the language part of an extended value against the RFC 5646
  grammar that RFC 8187 refers to (`UTF-8'1'a` used to pass); lenient parsing still
  skips any language made of letters, digits and hyphens.
- Strict error offsets count from the start of the header as given; they used to count
  from the header without its leading spaces. Messages end with `at offset N`.
- `is_attachment` is false for a type that is not a token, which only lenient parsing
  produces (an empty header, `"attachment"` in quotes, a header without a type): RFC 6266
  section 3 ignores invalid headers, and Chrome treats them as inline. It used to be
  true. `inline` is now also recognised without case on a value built by hand.
- Lenient parsing reads a header without a type (`filename=report.pdf`) as browsers do:
  the text before the first `;` stays the type and is also read as a parameter.
- `safe_filename` normalises again after removing invisible characters, so its result
  is always NFKC and passing it again returns it unchanged (`C`, zero-width space,
  combining acute gave `C` plus the combining accent; now `Ć`).
- `safe_filename` checks its arguments first: `max_bytes` must be an `int` (not a `bool`)
  of at least 1 whatever the name (`safe_filename(None, max_bytes=0)` returned the
  default), `default` a `str` and `name` a `str` or `None`, each with a `TypeError`.
- `ContentDisposition` refuses fields that are not `str` (`params` must be a `dict` of
  `str` to `str`) with `TypeError`.
- `ContentDisposition` shows and pickles as `contentdisp.ContentDisposition` instead of
  the private module; pickles made by 0.2.1 still load.

### Fixed

- `safe_filename` and `build` took quadratic time on a long run of combining marks of
  alternating classes (U+0316 U+0301 ...) or of characters that decompose into marks
  (U+0F73): a 64 KB name took over a second. Both are now linear.
- Error messages quote at most 40 characters of any input and never an extended value;
  a huge header, type or name used to be quoted whole.
- Lenient parsing checks a parameter name before lower-casing it, so the Kelvin sign no
  longer passes as `k`.
- A strict quoted-string cut off right after a backslash is reported as unterminated, at
  the end of the header.

### Added

- `ContentDispositionError`, a `ValueError` subclass with the `position` of the first
  offending character for strict parsing, raised for every invalid value.
- Runnable examples in every public docstring, run as doctests, and a GUIDE.
- Tests against the RFC 6266, RFC 8187, RFC 9110, RFC 5646, RFC 5234 and RFC 7578 texts
  as fetched by `scripts/fetch_upstream.py` (grammar rules compiled from the text), the tc2231 corpus,
  Chromium's unit test expectations, Microsoft's file naming rules, the HTML standard's
  form-data rule, the jshttp `content-disposition` 1.0.1 and 3.0.0 parsers run with
  Node.js, werkzeug, aiohttp, multipart, Python's `email` and `ntpath.isreserved`, real
  files created on Windows, and the 0.2.1 release; seeded fuzz and hostile input tests.

## [0.2.1] - 2026-10-13

### Changed

- The tc2231 browser corpus is no longer committed or shipped in the sdist:
  `scripts/fetch_upstream.py` fetches the page, checked against
  `tests/upstream/MANIFEST.json`, and hand-written cases keep the default suite meaningful
  without it.

## [0.2.0]

### Added

- `parse(header, strict=True)` rejects anything outside the RFC 6266 grammar, a
  repeated parameter, and a `name*` value that is malformed or holds octets invalid in
  its charset, with a `ValueError` that says where.
- `safe_filename(name)` reduces an advisory name to a harmless one as RFC 6266 section
  4.3 asks: last path segment only, control and invisible format characters removed,
  Windows reserved characters and device names neutralised, leading dots stripped,
  length capped in UTF-8 bytes with the extension kept.
- `ContentDisposition.is_attachment`: unknown disposition types count as attachment.
- `parse` accepts raw `bytes`, decoded as ISO-8859-1.
- Tests against the RFC 6266 and RFC 8187 examples, every case of the browser test
  corpus, and a grammar oracle on random headers; an installed-wheel end-to-end test.

### Changed

- A `filename*` that is malformed, undecodable or in a charset other than UTF-8 or
  ISO-8859-1 is now ignored, so the plain `filename` is used. It used to replace the
  file name with its raw text, and any Python codec could be named.
- Malformed percent escapes and quoted `filename*` values are no longer accepted.
- Repeated parameters keep the first value in lenient mode (it used to be the last).
- Lenient parsing replaces CR, LF and NUL with a space (RFC 9110 section 5.5).
- `build` raises `ValueError` for control characters (blocking header injection), for a
  type or parameter name that is not a token, and `TypeError` for non-string values.
- `build` follows RFC 6266 Appendix D: names with `\`, `"` or a `%HH` sequence get an
  ASCII fallback with `_` plus an exact `filename*`, instead of backslash escapes;
  accented letters fall back to their base letter instead of `_`.
- `build("form-data", ...)` never writes `filename*` (RFC 7578 section 4.2): non-ASCII
  names stay UTF-8 and CR, LF, `"` and `\` are percent-escaped.
- `build` rejects a parameter given twice (names compare case-insensitively, `_` as `-`).
- Strict parsing accepts any non-ASCII character of a `str` inside a quoted-string.
- Documentation cites RFC 8187, which obsoletes RFC 5987.

## [0.1.0]

- Parse a Content-Disposition header into type, filename and parameters, preferring
  the decoded RFC 5987 `filename*` over the plain fallback.
- Build a header from its parts, emitting an ASCII fallback plus a correct `filename*`
  for non-ASCII names.
- Tolerate malformed parameters, bad extended values and unknown charsets on parse.
