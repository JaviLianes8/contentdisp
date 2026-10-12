# contentdisp improvement round

Progress:
- [x] Brainstorm ranked improvements (this file)
- [x] Parser: RFC 6266 grammar, strict mode, lenient recovery, bytes input
- [x] Extended values: RFC 8187 grammar, UTF-8 and ISO-8859-1 only, bad values ignored
- [x] `safe_filename`: path traversal, device names, control and bidi characters, length
- [x] Builder: header injection blocked, Appendix D fallback, form-data per RFC 7578
- [ ] Contracts: RFC examples, browser corpus, grammar oracle, typing, README examples
- [ ] Installed wheel e2e test
- [ ] Docs: README, CHANGELOG, docstrings, packaging metadata
- [ ] Gates: ruff format, ruff check, mypy --strict, pytest
- [ ] Independent review findings fixed with regression tests
- [ ] Pull request opened, guard clean

## Starting point

`0.1.0` parses and builds the header and decodes `filename*`. Reading it against the
current specifications and the browser test corpus turned up these gaps:

- Anything is accepted. `attachment; filename="bar` (unterminated), `inline; attachment`,
  `filename=foo.html` (no type) and duplicated parameters all parse without complaint,
  and there is no way to ask whether a header is valid.
- A `filename*` that fails to decode replaces a good `filename` with its raw text
  (`UTF-8'foo` becomes the file name). RFC 8187 says to ignore such a parameter, and the
  plain `filename` fallback exists exactly for that case.
- Any Python codec named in `filename*` is used to decode it, and ISO-8859-1 accepts
  octets 0x80-0x9F that are not ISO-8859-1 characters.
- Malformed percent escapes (`foo%`, `f%oo`) and quoted extended values are accepted.
- The parsed file name is handed back as is: `../../etc/passwd`, `C:\Windows\x.dll`,
  `CON`, control characters and right-to-left overrides reach the caller, who has to
  know RFC 6266 section 4.3 to clean them.
- `build` writes CR and LF straight into the header (`build("attachment", "a\r\nSet-Cookie: x")`),
  and accepts a disposition type or parameter name that is not a token.
- `build` puts `\` and `"` in the quoted fallback and leaves `%41` there, all three
  things Appendix D says to avoid; non-ASCII letters become `_` instead of their ASCII base.
- `build("form-data", "é.txt")` emits `filename*`, which RFC 7578 section 4.2 forbids.

## Sources (fetched 2026-10-12)

- RFC 6266: https://www.rfc-editor.org/rfc/rfc6266.txt
  (sha256 2887d464e7a2a15877aba5d54b2e8e0c06c32294c44c9d95eb8940069ab43d33).
  4.1 grammar, 4.2 disposition type, 4.3 filename and its security list, section 5
  examples, Appendix D advice for generating the field.
- RFC 8187: https://www.rfc-editor.org/rfc/rfc8187.txt
  (sha256 af50e65257dc16a27fa85e25ef68d49c8fa2a4abc21094a00469462c8cb89b53).
  3.2.1 ext-value grammar and error handling, 3.2.3 examples, 4.2 precedence.
- RFC 9110: https://www.rfc-editor.org/rfc/rfc9110.txt
  (sha256 21c1cdce6ab0e5509b04d84a28000836c7a087cf786efe6f04877ebfff47232a).
  5.5 field values (CR, LF and NUL), 5.6.2 token, 5.6.3 OWS, 5.6.4 quoted-string.
- RFC 7578: https://www.rfc-editor.org/rfc/rfc7578.txt
  (sha256 813277f91c6c65c9047da9e9a8f1f0c19c1fb4bb1aaeea944bcf3bbdcc2eef49). 4.2.
- Browser test corpus (the one RFC 6266 Appendix D points to):
  http://greenbytes.de/tech/tc2231/
  (sha256 341d2916ce946f670567f40ce570115d08873f51794aac13ad62047b7e7a6896).

## Ranked improvements

1. **RFC 6266 grammar, two modes.** `parse(header, strict=True)` raises `ValueError`
   on anything outside the grammar (type, `;` separators, token or quoted-string values,
   duplicate names, invalid `filename*`). The default lenient mode never raises: it
   follows the grammar where the header is valid and recovers per parameter where it is
   not, so both modes agree on every valid header.
2. **Extended values per RFC 8187.** Full ext-value grammar; UTF-8 (required) and
   ISO-8859-1 (encouraged) only; a parameter that fails to parse or decode is ignored,
   so the plain `filename` wins.
3. **`safe_filename`.** Turns an advisory name into one that can be written inside a
   folder: last path segment only (`/` and `\`), NFKC so full-width slashes are caught,
   control and bidi characters removed, Windows reserved characters and device names
   neutralised, leading dots and trailing dots or spaces stripped, length capped in bytes
   with the extension kept, and a default when nothing is left.
4. **Ground truth.** Every Content-Disposition example of RFC 6266 section 5 and every
   ext-value example of RFC 8187 3.2.3 and 4.2, plus all 89 cases of the browser corpus,
   extracted from the fetched pages by a committed script with the URL and hash recorded.
5. **Builder hardening.** CR, LF, NUL and other controls rejected; type and parameter
   names must be tokens; the fallback follows Appendix D (ASCII transliteration, no `\`,
   `"` or `%HH`), with `filename*` added whenever the fallback is not exact.
6. **form-data.** Per RFC 7578 4.2 no `*` parameter is emitted; non-ASCII stays as
   UTF-8 text in the quoted string.
7. **Grammar oracle.** A regular expression derived by hand from the RFC 6266 ABNF
   (labelled as such) checked against seeded random and mutated headers: strict mode
   accepts exactly what the oracle accepts, and lenient equals strict on those.
8. **Typed public API, proven.** mypy reveals the documented types and rejects wrong
   argument types. `parse` takes `str` or Latin-1 `bytes`.
9. **`is_attachment`.** Unknown disposition types count as attachment (4.2).
10. **Docs and packaging.** Every README example runs in the suite, API table complete,
    CHANGELOG with the behaviour changes, classifiers, version checks, installed-wheel
    e2e test.

## Out of scope

- RFC 2231 continuations (`filename*0`, `filename*1`): RFC 6266 does not adopt them
  and browsers disagree; they stay ordinary extension parameters. The corpus cases that
  expect them are listed in the test as deliberately not followed.
- RFC 2047 encoded words and percent-decoding of plain `filename`: Appendix C rejects
  both, and the corpus checks that they are not applied.
- A command line tool: the header is read and written inside HTTP code, and
  `curl -OJ` already saves a download under its advertised name.
