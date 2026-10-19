# contentdisp guide

The behaviour of every public name in detail. Each Python block below runs as a test: a
comment line after a `print` holds what it prints.

## Reading a header: two modes

`parse(header, *, strict=False)` takes the field value as `str` or `bytes`. Bytes are
decoded as ISO-8859-1, so every octet survives as one character: RFC 6266 section 4.3
gives the plain `filename` the ISO-8859-1 repertoire (only `filename*` goes beyond it),
and RFC 9110 section 5.5 treats other octets as opaque. A part header of a
`multipart/form-data` body is UTF-8: decode it yourself and pass `str`.

**`strict=True`: exactly the grammar.** RFC 6266 section 4.1, with `token`,
`quoted-string` and the whitespace allowed around separators as RFC 9110 defines them
(RFC 2616, which RFC 6266 cites, is obsolete), and `ext-value` as RFC 8187 section 3.2.1
defines it, its language part an RFC 5646 language tag.

- Spaces and tabs may surround the value and every `;` and `=`; CR, LF and NUL may not
  appear anywhere (RFC 9110 section 5.5).
- A value is a token or a quoted-string; a name ending in `*` takes an extended value
  (`charset'language'value`), never a quoted one. RFC 6266 defines that name as a token
  followed by `*`, so `*` alone is an ordinary name with an ordinary value, and `**` is
  its extended form.
- A parameter given twice is an error (names compare without case; `filename` and
  `filename*` are different names).
- In a `str`, every character above U+00FF counts as `obs-text`: the text was decoded
  already, whatever its encoding.
- Extended values are decoded in UTF-8 and ISO-8859-1. Octets invalid in the charset
  (bad UTF-8) are an error, and so is decoded text holding a control other than HTAB
  (U+0000 to U+0008, U+000A to U+001F and U+007F to U+009F) in either charset: ISO/IEC
  8859-1 has no graphic character there, `build` refuses the same characters, and a file
  name is valid or not whatever its charset label. A value in any other charset is well
  formed but not understood, so the parameter is ignored, in both modes.
- `ContentDispositionError.position` is the index of the first character that breaks
  the grammar, a CR, LF or NUL included, or the end of the header when it stops too
  early. Two errors point at the start of a part instead: an extended value whose octets
  are invalid in its charset or decode to a control (its grammar holds) points at the
  start of the value, and a language part made of letters, digits and hyphens, closed by
  its `'`, that is not a well-formed tag points at its first character, even when a later
  character of the value breaks the grammar too. A language part that is not closed (the
  value ends, or another character follows it) points at its first character that no
  tag can continue with: `UTF-8'-en` at the `-`, `0%'c0` at the `0`; when every tag
  could still go on (`UTF-8'en-`), the grammar error after it stands.

```python
from contentdisp import ContentDispositionError, parse

try:
    parse("attachment; filename*=UTF-8'en_US'report.pdf", strict=True)
except ContentDispositionError as error:
    print(error)
# malformed extended value for 'filename*' at offset 30
print(parse("attachment; filename*=x-mac-roman''r%E9sum%E9.pdf", strict=True).params)
# {}
```

**Default: recover what can be read.** RFC 6266 section 3 lets a recipient recover a
usable value from an invalid header. On every valid header the result equals the strict
one; on the others:

- The type is the text before the first `;` outside quotes, without surrounding spaces,
  lower-cased, whatever it holds. When that text has the form `name=value` (a server that
  forgot the type) it is also read as a parameter, as Chrome and Firefox do.
- A segment without `=`, or whose name is not a token, is skipped; so is an extended
  value that does not decode or decodes to a control other than HTAB, which lets the
  plain `filename` win. So no value holds a CR, LF or NUL, raw or percent-encoded.
- The first of a repeated parameter wins.
- A quoted value ends at its closing quote (text after it is ignored) or, unterminated,
  at the end of the header; an unquoted value is taken as written, spaces included.
- CR, LF and NUL become spaces.
- The language part of an extended value is skipped as long as it is made of letters,
  digits and hyphens.

```python
from contentdisp import parse

print(parse('attachment; filename="a b.pdf"x; filename=other.pdf').filename)
# a b.pdf
print(parse("filename=report.pdf").params, parse("filename=report.pdf").is_attachment)
# {'filename': 'report.pdf'} False
print(parse("attachment; filename=plain.pdf; filename*=UTF-8''%FF").filename)
# plain.pdf
```

## The value: `ContentDisposition`

A frozen dataclass with `type` and `params`. `parse` lower-cases the type and the names
and stores a decoded `name*` under `name`, where it overrides the plain value (RFC 6266
section 4.3, RFC 8187 section 4.2). Its fields cannot be reassigned, but `params` is the
plain `dict` it was given, so the value is not hashable. Built by hand, it is stored as
given, and both fields must hold `str` (`TypeError` otherwise). It pickles and copies;
pickles made by 0.2.1 still load.

- `filename`: `params.get("filename")`, the decoded `filename*` when there was one.
- `is_attachment`: true for `attachment` and every other token except `inline`, compared
  without case, since RFC 6266 section 4.2 treats an unknown type as `attachment`. False
  for `inline` and for a type that is not a token, which only lenient parsing produces:
  such a header is invalid, and an invalid header is ignored (RFC 6266 section 3), which
  is what Chrome does too.

```python
from contentdisp import ContentDisposition, parse

print([parse(h).is_attachment for h in ("attachment", "x-zip", "Inline", '"attachment"', "")])
# [True, True, False, False, False]
print(ContentDisposition("attachment", {"filename": "a.pdf"}).filename)
# a.pdf
```

## Writing a header: `build`

`build(type, /, filename=None, **params)` returns the field value. The type is
lower-cased (surrounding whitespace removed); keyword names use `-` for `_` and are
lower-cased; every value is written as a quoted-string, in the order given, `filename`
first. The type is positional only, so `type` itself can be a keyword parameter.

In place of the type, `build` takes a `ContentDisposition`: its type and parameters are
written first, names as they are (lower-cased), then `filename` and the keywords. This
writes a parsed header again, `build(parse(header))`, and reaches the names a keyword
cannot spell, such as `x_y` or `*`. Four kinds of parsed header cannot be written
again, and `build` refuses them with `ContentDispositionError`: a type that is not a
token, which only lenient parsing returns; a name ending in `*`, which parsing returns
for an extended parameter whose own name ends in `*` (`a**=UTF-8''x` gives `a*`, and
`build` never writes an extended name); a value holding a control character, such as a
C1 control (U+0080 to U+009F), which RFC 9110 obs-text lets into a quoted-string; and a
value holding a lone surrogate (U+D800 to U+DFFF), which a `str` can carry and parsing
takes as obs-text like any other character above U+00FF.

Following RFC 6266 Appendix D, when the plain form cannot carry a value faithfully
(non-ASCII, a `\` or `"`, or a `%` followed by two hex digits, which some agents decode)
an ASCII fallback is written first and the exact value follows as `name*` in UTF-8.
The fallback drops accents (`é` becomes `e`) and writes `_` for anything else. Other
parameters get the same treatment.

For `form-data` (RFC 7578 section 4.2) no `name*` parameter is ever written: values stay
UTF-8, and LF, CR and `"` become `%0A`, `%0D` and `%22`, as the HTML standard tells
browsers to do. `build` also writes a backslash as `%5C`, one escape more than browsers:
left raw, it would escape the closing quote for an RFC 9110 parser and swallow the next
parameter. A receiver that only decodes the browser escapes sees `%5C`.

A type or name that is not a token, an extended name (a token followed by `*`), a name
given twice, and a value holding a control character other than tab (CR and LF are
escaped for `form-data`) or a lone surrogate raise `ContentDispositionError`; an argument
of the wrong type raises `TypeError`. No value can split the header.

```python
from contentdisp import ContentDispositionError, build, parse

print(build("attachment", "naïve 100%41.txt", creation_date="Wed, 12 Feb 1997"))
# attachment; filename="naive 100_41.txt"; filename*=UTF-8''na%C3%AFve%20100%2541.txt; creation-date="Wed, 12 Feb 1997"
print(build("form-data", 'my "cv".pdf', name="file"))
# form-data; filename="my %22cv%22.pdf"; name="file"
try:
    build("attachment", "a.txt\r\nSet-Cookie: x=1")
except ContentDispositionError as error:
    print(error)
# parameter 'filename' contains a control character: '\r'
print(build(parse("Attachment; x_y=1; type=2")))
# attachment; x_y="1"; type="2"
```

## Saving the file: `safe_filename`

`safe_filename(name, *, default="download", max_bytes=255)` applies the rules of RFC
6266 section 4.3 and Microsoft's file naming rules, in this order:

1. NFKC normalisation, so full-width slashes and dots become real ones. Before it, every
   run of more than 30 non-starters (characters with a non-zero canonical combining
   class, counted on the NFKD decomposition) loses the ones after the 30th, which keeps
   the time linear on hostile names; marks of class 0, such as U+20DD or U+093F, are
   never dropped. The limit of 30 comes from the Unicode Stream-Safe Text Format (UAX
   #15), but UAX #15 keeps every non-starter and splits the run with U+034F COMBINING
   GRAPHEME JOINER; this library drops them, since no file name needs them. The ASCII
   fallback of `build` does the same.
2. Only the text after the last `/` or `\` is kept.
3. Control characters, lone surrogates and invisible format characters (bidi controls,
   zero-width spaces, soft hyphens) are removed, except the joiners inside emoji and
   scripts; other whitespace becomes a space. Then NFKC again (with the same cut), so
   the result is normalised.
4. `< > : " | ? *` become `_` (`:` would also open an NTFS stream).
5. Leading spaces, dots, `~`, `-`, joiners and combining marks go, and trailing spaces
   and dots.
6. The name is cut to `max_bytes` of UTF-8, keeping the last extension when it takes at
   most 16 bytes and half the budget, never splitting a character or leaving the
   extension alone.
7. A Windows device name (`CON`, `PRN`, `AUX`, `NUL`, `CONIN$`, `CONOUT$`, `COM0`-`COM9`,
   `LPT0`-`LPT9`, with superscript digits too), with or without an extension, gets a `_`
   in front.

When nothing usable is left, `default` is returned unchecked, as a plain `str`. Otherwise
the result is a fixed point: passing it again returns it unchanged. `max_bytes` must be an
`int` of at least 1 (`TypeError`, `ContentDispositionError`), checked whatever the name.

```python
from contentdisp import safe_filename

print(safe_filename("..\\..\\boot.ini"), safe_filename("nul .tar.gz"), safe_filename("~/.bashrc"))
# boot.ini _nul .tar.gz bashrc
print(safe_filename("\N{RIGHT-TO-LEFT OVERRIDE}fdp.exe"), safe_filename("a:b?.txt"))
# fdp.exe a_b_.txt
print(safe_filename("..", default="file.bin"), safe_filename("x" * 300 + ".tar.gz", max_bytes=20))
# file.bin xxxxxxxxxxxxxxxxx.gz
```

## Errors

| Error | Raised by | When |
| --- | --- | --- |
| `ContentDispositionError` | `parse(..., strict=True)` | the header breaks the grammar; `position` is set |
| `ContentDispositionError` | `build` | a type or name is not a token, a name repeats or is an extended name, a value holds a control character or a lone surrogate |
| `ContentDispositionError` | `safe_filename` | `max_bytes` is below 1 |
| `TypeError` | all | an argument has the wrong type |

`ContentDispositionError` is a `ValueError`, so `except ValueError` still catches it.
Messages quote at most 40 characters of any input and never quote an extended value, so a
huge or sensitive header stays out of logs. Lenient parsing raises nothing but
`TypeError` for an argument that is not `str` or `bytes`.

## Not supported on purpose

- RFC 2231 parameter continuations (`filename*0`, `filename*1`): RFC 8187 section 3.1
  leaves them out of HTTP. They stay ordinary parameters.
- RFC 2047 encoded words and percent-decoding of the plain `filename`: RFC 6266 Appendix
  C explains why both are inferior to `filename*`, and the browser test corpus checks
  that percent escapes are not decoded.
- Guessing the charset of raw octets in a plain `filename`, which Chrome does: RFC 6266
  Appendix C.3 calls it not interoperable.

## How it is tested

Against the RFC 6266, RFC 8187, RFC 9110, RFC 5646, RFC 5234 and RFC 7578 texts as fetched
(their grammar rules are compiled from the text, not retyped), the tc2231 browser test
corpus RFC 6266 points to, Chromium's own unit test expectations, Microsoft's file naming
rules and the HTML standard; against the jshttp `content-disposition` parsers run with
Node.js, against werkzeug, aiohttp, multipart and Python's `email` package, against
Python's `ntpath.isreserved` and real files created on Windows; and against the 0.2.1
release, with seeded fuzz and hostile input. `tests/upstream/MANIFEST.json` lists every
fetched source with its URL, revision, licence and SHA-256.
