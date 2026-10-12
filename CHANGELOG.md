# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
