# contentdisp 1.0.0 certification report

The 1.0.0 certification bar (19 items) applied to contentdisp. PyPI has 0.2.1, whose
modules are byte for byte the ones on `main` at 01f5819 (the wheel compared with the tree),
so every change listed here is a change against the PyPI release.

Progress:
- [x] Branch `release/1.0.0` created from `main` (01f5819, same code as PyPI 0.2.1)
- [x] API review and 1.0.0 changes (item 1)
- [x] Errors, typing, docstrings and doctests (items 2 to 5)
- [x] Ground truth: specifications, browser expectations and reference parsers (item 7)
- [x] Contract, fuzz and hostile input (items 6, 9)
- [x] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [x] Packaging, e2e and upgrade from PyPI 0.2.1, every Python (items 8, 10, 13, 14)
- [x] Author mutation round (item 18)
- [x] Gates (item 15)
- [ ] Five QA lenses report PASS (item 19): rounds 1 to 6 findings fixed, re-verification pending
- [ ] Independent reviewer reports PASS (item 16)
- [x] PR #4 opened, trace guard CLEAN (item 17); merge and publish left to the maintainer

## Scorecard

| # | Item | Result |
| --- | --- | --- |
| 1 | Public API reviewed for stability | PASS: the five names of 0.2.1 kept, signatures pinned by `tests/test_contract_api.py`; one name added (`ContentDispositionError`); `build` takes its type positional only and also a `ContentDisposition` (QA round 1, finding A1); every behaviour change in the CHANGELOG and the GUIDE, each checked against 0.2.1 |
| 2 | `__all__` exact, no private imports in docs | PASS |
| 3 | Docstrings with runnable examples, doctests | PASS: 26 doctest examples in 7 docstrings; README and GUIDE examples run as tests with their printed output |
| 4 | Typed end to end | PASS: `mypy --strict src tests`, `py.typed` shipped, types inferred from a consumer checked by `tests/test_typing.py` |
| 5 | Typed, documented, bounded errors | PASS: `ContentDispositionError` (a `ValueError`) with `position`; `TypeError` for wrong argument types; messages quote at most 40 characters and never an extended value |
| 6 | Contract tests of every public name | PASS |
| 7 | Real ground truth | PASS: 12 fetched sources with a hash manifest, Chromium's expectations, the jshttp parsers run with Node.js, werkzeug, aiohttp, multipart, `email`, `ntpath.isreserved`, real files on Windows, PyPI 0.2.1 |
| 8 | Real e2e from the wheel | PASS: wheel and sdist built and inspected, wheel installed in a fresh venv and driven from an empty folder, 0.2.1 from PyPI upgraded in place; no CLI exists |
| 9 | Seeded fuzz, no crash, hang or blowup | PASS |
| 10 | Supported Pythons | PASS: CPython 3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2, 3.14.2t; 3.8 and 3.9 are below `requires-python` |
| 11 | README and `twine check` | PASS: `twine check --strict` on both files, absolute links, problem, why, install, quick start |
| 12 | Dated CHANGELOG section | PASS: 1.0.0, 2026-10-19 |
| 13 | pyproject 1.0.0, Production/Stable | PASS |
| 14 | sdist and wheel contents | PASS |
| 15 | Gates each exit 0 | PASS: see Gates |
| 16 | Independent reviewer | pending |
| 17 | PR and trace guard | PR #4 from `release/1.0.0`, trace guard CLEAN; merge and publish left to the maintainer |
| 18 | Contracts bite (mutations) | PASS: 24 author mutants, 23 killed at once, the survivor killed by a contract added in b81458e |
| 19 | Five independent QA lenses | pending |

## API review (item 1)

Kept: `parse(header, *, strict=False)`, `ContentDisposition(type, params)` with
`filename` and `is_attachment`, and `safe_filename(name, *, default="download",
max_bytes=255)`, with the parameter names and defaults of 0.2.1. Changed in QA round 1:
`build(type, /, filename=None, **params)` takes its type positional only (so `type` can
be a keyword parameter) and accepts a `ContentDisposition` in its place, written with
its names as they are, so `build(parse(header))` writes any parsed header again. Added: `ContentDispositionError`, a `ValueError` subclass, so
`except ValueError` keeps working. Changed, all in the CHANGELOG with a test against
0.2.1 (`tests/test_upgrade.py`): strict language tags (RFC 5646), strict offsets counted
from the start of the header, `is_attachment` false for a type that is not a token,
lenient reading of a header without a type, `safe_filename` idempotent (NFKC after
removing invisible characters) and checking its arguments first, `ContentDisposition`
refusing non-`str` fields, bounded messages, the Kelvin sign no longer read as `k`, the
public classes shown and pickled as `contentdisp.<Name>` (a 0.2.1 pickle still loads).

## Ground truth (item 7)

Fetched on 2026-10-18 by `scripts/fetch_upstream.py` into the ignored `tests/upstream`
folder; `tests/upstream/MANIFEST.json` records URL, revision, size, sha256, licence and
date, and the tests check the hash before reading. Nothing fetched is committed or shipped.

- RFC 6266, RFC 8187, RFC 9110, RFC 5646, RFC 5234 and RFC 7578 from rfc-editor.org:
  the grammar rules are compiled from the ABNF in the text (`tests/abnf.py`,
  `tests/test_spec_grammar.py`) and compared with the strict parser; every example
  header is cut from the text (`tests/test_spec_examples.py`).
- greenbytes tc2231 (https://greenbytes.de/tech/tc2231/): every case read from the page
  (`tests/test_browser_corpus.py`).
- Chromium `http_content_disposition_unittest.cc` at commit 981a92d: the expected file
  names read from the test tables (`tests/test_chromium_corpus.py`).
- WHATWG HTML commit snapshot de953a7: the form-data escaping rule; Microsoft Learn
  naming rules at commit 63e7090: reserved names and characters, also checked by creating
  real files on Windows (`tests/test_windows_names.py`).
- jshttp `content-disposition` 1.0.1 and 3.0.0 from the npm registry, run with Node.js
  (`tests/test_oracles_node.py`); werkzeug 3.1.9, aiohttp 3.14.5, multipart 2.0.1 and
  `email` read back every built header (`tests/test_oracles_python.py`).
- PyPI 0.2.1 as an oracle (`tests/test_upgrade.py`, `CONTENTDISP_V021`): same results
  except the documented changes, each asserted case by case.

## Fuzz and hostile input (item 9)

`tests/test_fuzz.py` with seeded generators (`tests/generators.py`): lenient parsing
never fails and returns clean text, strict parsing raises only
`ContentDispositionError`, build round trips through both modes, `safe_filename` is
idempotent and safe. `tests/test_hostile.py`: input shapes timed at growing sizes (linear),
a 4 MB header in both modes, 1 MB inputs in every error path with the exact 40 character cut.

## Author mutation round (item 18)

Each mutant was applied alone to a fresh clone of `release/1.0.0` at 8e49dcb on another
machine (CPython 3.14), with the fetched sources, Node.js and the two jshttp parsers,
werkzeug 3.1.9, aiohttp 3.14.5, multipart 2.0.1 and the 0.2.1 oracle present, and the full
suite run with `-x` and a 300 s per-test limit. The first failing test is listed. The
unmutated suite passed after the round.

| Mutant | Module | Change | Killed by |
| --- | --- | --- | --- |
| M01 | `_grammar.py` | tchar drops the backtick | `test_oracles_node.py::test_strict_mode_agrees_with_release_1_on_the_shared_grammar` |
| M02 | `_grammar.py` | qdtext upper bound off by one (DEL allowed) | `test_positions.py::test_strict_errors_point_at_the_first_offending_character` |
| M03 | `_grammar.py` | quoted-pair drops the escaped character | `test_browser_corpus.py::test_the_offered_file_name_matches_the_corpus` |
| M04 | `_grammar.py` | unterminated quoted-string position off by one | `test_positions.py::test_strict_errors_point_at_the_first_offending_character` |
| M05 | `_ext_value.py` | ISO-8859-1 octets 0x80 to 0x9F accepted | `test_browser_corpus.py::test_strict_mode_rejects_exactly_what_the_corpus_marks_invalid` |
| M06 | `_ext_value.py` | encoder leaves `%` unescaped | `test_build.py::test_characters_appendix_d_avoids_move_to_the_extended_form` |
| M07 | `_langtag.py` | numeric region of two digits instead of three | `test_spec_grammar.py::test_language_tags_are_exactly_the_rfc_5646_rule` |
| M08 | `_parse.py` | strict mode accepts repeated parameters | `test_browser_corpus.py::test_strict_mode_rejects_exactly_what_the_corpus_marks_invalid` |
| M09 | `_parse.py` | plain `filename` overrides `filename*` | doctest `contentdisp.ContentDisposition.filename` |
| M10 | `_parse.py` | lenient mode keeps the last repeated parameter | doctest `contentdisp._parse.parse` |
| M11 | `_parse.py` | lenient mode keeps NUL | `test_fuzz.py::test_lenient_parsing_never_fails_and_returns_clean_text` |
| M12 | `_parse.py` | segment splitter ignores backslash escapes | `test_browser_corpus.py::test_the_offered_file_name_matches_the_corpus` |
| M13 | `_parse.py` | ext-value error points after the value, not its start | `test_docs.py::test_every_guide_example_runs_and_prints_its_comment` |
| M14 | `_build.py` | form-data leaves a backslash raw | `test_build.py::test_form_data_escapes_only_cr_lf_quote_and_backslash` |
| M15 | `_build.py` | ASCII fallback keeps `%HH` sequences | `test_build.py::test_characters_appendix_d_avoids_move_to_the_extended_form` |
| M16 | `_build.py` | duplicate names compared with case | `test_build.py::test_extra_parameters_use_hyphens_and_lower_case` |
| M17 | `_safe.py` | device name `CONIN$` dropped | `test_safe_filename.py::test_windows_device_names_are_prefixed` |
| M18 | `_safe.py` | truncation budget off by one | `test_docs.py::test_every_guide_example_runs_and_prints_its_comment` |
| M19 | `_safe.py` | extension taken after the first dot | `test_docs.py::test_every_guide_example_runs_and_prints_its_comment` |
| M20 | `_safe.py` | joiners removed like other format characters | `test_safe_filename.py::test_format_characters_are_removed_but_joiners_inside_a_name_stay` |
| M21 | `_model.py` | `is_attachment` compares `inline` with the wrong case | doctest `contentdisp.ContentDisposition` |
| M22 | `_errors.py` | message cut keeps 40 characters plus `...` (43) | survived at 8e49dcb; killed at b81458e by `test_hostile.py::test_huge_input_never_reaches_a_message_whole` |
| M23 | `_ext_value.py` | strict mode skips the language tag check | `test_oracle.py::test_strict_mode_accepts_exactly_what_the_oracle_accepts` |
| M24 | `_model.py` | `params` values not type checked | `test_contract_api.py::test_wrong_argument_types_raise_type_error` |

M22 showed that no test pinned the exact length of the quoted input in a message (the
old check only refused 41 repeated characters). The contract added in b81458e asserts
the cut is exactly 40 characters (opening quote, 36 characters, `...`); M22 applied to
that commit fails it.

## Packaging, e2e and Pythons (items 8, 10, 13, 14)

- `tests/test_e2e_wheel.py` (`CONTENTDISP_E2E=1`, `CONTENTDISP_E2E_PYPI=1`): builds the
  wheel and sdist; the wheel holds exactly the modules (ten since QA round 1), `py.typed`, LICENSE and its
  metadata (1.0.0, Production/Stable, Python 3.14 classifier, project URLs, no runtime
  requirement); the sdist holds the sources, tests, MANIFEST and docs, no fetched file,
  no report, no scripts but the two the tests use; the wheel installed in a fresh venv is
  driven from an empty folder with `-I`; 0.2.1 from PyPI is upgraded in place and
  checked before and after. Passed on another machine from a fresh clone at 8e49dcb.
- `twine check --strict` passed on the wheel and the sdist built from a fresh clone at
  8e49dcb.
- Every interpreter on this PC from `requires-python` up, at 8e49dcb: the wheel in a
  fresh venv and the sdist's own suite run with `src` removed (fetched sources, Node.js,
  werkzeug, aiohttp, multipart and the 0.2.1 oracle present). CPython 3.10.19, 3.11.5,
  3.12.12: 454 passed, 5 skipped; 3.13.2, 3.14.2 and 3.14.2t: 455 passed, 4 skipped. The
  skips are the four e2e tests (run separately above) and, below 3.13, the
  `ntpath.isreserved` comparison, which that function needs.

## Gates (item 15)

Latest run at 13fe189 on Elena's PC (Python 3.14.2) from a fresh clone, each command on
its own, with the fetched sources, Node.js, werkzeug, aiohttp, multipart, the 0.2.1
oracle, `CONTENTDISP_E2E=1` and `CONTENTDISP_E2E_PYPI=1`: `ruff format --check .`,
`ruff check .`, `mypy --strict src`, `mypy --strict src tests` and `pytest` (800 passed,
no skip) all exit 0. Earlier runs after each QA round are listed with that round below.

## QA lenses (item 19)

### Round 1 (lenses a, b, c and e at 6937470)

Lens b (ground truth) also reported everything else it re-derived as matching: the 89
tc2231 responses, the RFC 6266 and RFC 8187 examples, RFC 5646 Appendix A, an
independent ABNF oracle over 90,000 headers, error positions, Chromium's expectations,
built headers read by an oracle and by jshttp, and `safe_filename` on the real Windows
file system. Lens c (adversarial) ran 1.62 million fuzz cases without a failure besides
its finding. Every finding below is fixed in e1284bd (tests in b653a6a adjusted for the
documented change); none is disputed.

| Id | Finding | What changed |
| --- | --- | --- |
| a/A1 | `build` could not write `type` (it clashed with the first argument) nor a name with `_` | `type` is positional only; `build` also takes a `ContentDisposition`, written with its names as they are, so `build(parse(header))` writes any parsed header again. Tests: `tests/test_build_params.py`; signature pin updated; CHANGELOG Changed |
| a/A2 | CHANGELOG had no Added entry for `ContentDispositionError` and implied it existed before | Added entry; the pickling bullet names only `ContentDisposition` |
| a/A3 | CHANGELOG said the RFC texts are fetched at test time | Now says they are fetched by `scripts/fetch_upstream.py` |
| a/A4 | `parse` docstring: lenient type is the text before the first `;` | Now "the first `;` outside quotes" |
| a/A5 | A lone surrogate was reported as a control character | Message says `a lone surrogate`; test pins both messages; CHANGELOG Changed |
| a/A6 | CONTRIBUTING contradicted the tests (no real disk or subprocess; only tc2231 fetched) | Rewritten: every fetched source, the optional tools and the tests that touch real files and subprocesses |
| b/F1 | A bare `*` was read as an extended name (RFC 6266 ext-token is a token followed by `*`) | `*` alone is an ordinary name in both modes and in `build`; `**` is its extended form. Contract tests in `tests/test_grammar_edges.py` and `tests/test_build_params.py` failed first; the regex oracle in `tests/test_oracle.py` and the 0.2.1 comparison follow the rule; GUIDE and CHANGELOG |
| c/F1 | `safe_filename` and `build` were quadratic on runs of combining marks | New `_unicode.normalize` cuts every run of non-starters, counted on the decomposition, to 30 (UAX #15 Stream-Safe) before normalising. Linear-time tests for alternating classes, U+0F73 and runs split by invisible characters, all failing before. On Elena's PC (Python 3.14.2): 1M characters now take 0.17 to 0.23 s in `safe_filename` and 0.31 to 0.40 s in `build` (lens c measured 1.3 s for 64k before) |
| e/F1 | Language-tag mutants L03, L05, L07, L09 survived | `tests/test_grammar_edges.py`: every grandfathered tag, 0 to 3 extlangs and 4 refused, 2-digit region refused, 4, 5 and 8-letter language and 9 refused, extension subtags of 1 and 9 characters refused |
| e/F2 | Extension budget mutant S05 survived | 16-byte extension kept and 17 dropped; half of a small budget |
| e/F3 | `show` never raising was not pinned (E05) | A key or value whose `__repr__` raises gives the `TypeError` with `<_BadRepr>` |
| e/F4 | P16, G01, G02, X08, L06, B13 bit only with fetched files | Self-contained tests: the exact tchar set (every printable ASCII character), lenient unquoted spaces, empty charset, extension subtag length, NFKD transliteration of U+FB01 |

Mutants re-run after the fixes, each alone, against only the tests that need no fetched
file (on Elena's PC, fresh copy): L03, L05, L06, L07, L09, S05, E05, P16, G01, G02 and
X08 are killed, and so are two new ones (the bare `*` check removed, the mark-run cut
removed). B13 as written (NFKD to NFD in `ascii_fallback`) is now equivalent, because
the bounded normaliser already decomposes each character with NFKD; flipping both NFKD
uses is killed by `test_the_fallback_transliterates_compatibility_characters`.

Gates on Elena's PC (Python 3.14.2) from a clone of the branch, each on its own:
`ruff format --check .`, `ruff check .`, `mypy --strict src`, `mypy --strict src tests`
and `pytest` all exit 0, at e1284bd without fetched files (573 passed, 71 skipped) and at
b653a6a with them (620 passed, 24 skipped). At b653a6a with the fetched sources, Node.js,
werkzeug, aiohttp, multipart, the 0.2.1 oracle, `CONTENTDISP_E2E=1` and
`CONTENTDISP_E2E_PYPI=1`: 644 passed, no skip (the first run of this at e1284bd found the
0.2.1 comparison still expecting the old bare `*` reading, fixed in b653a6a).

Re-verification by the same lenses: done in round 2.

### Round 2 (lenses a, b, c and e at 7b14411)

Every round 1 finding was re-checked by the lens that raised it and reported fixed (lens
a: A1 to A5, A6 in part; lens b: F1; lens c: F1, now linear up to 1M characters; lens e:
every round 1 mutant killed). The new findings are below; none is disputed. Contract
tests for the two behaviour bugs (c/N1, c/N2) were added first and failed on 7b14411.

| Id | Finding | What changed |
| --- | --- | --- |
| a/N1 | CONTRIBUTING said the tests never reach the network, false for the opt-in e2e tests | The sentence now covers only the tests that read fetched files; the e2e paragraph says `python -m build` downloads the build backend and `CONTENTDISP_E2E_PYPI=1` installs 0.2.1 from PyPI |
| a/N2, b/F2 | GUIDE and CHANGELOG said the cut of a mark run to 30 is what UAX #15 does; UAX15-D4 keeps the marks and inserts U+034F | GUIDE step 1, the CHANGELOG entry and the `safe_filename` docstring now say the marks after the 30th are dropped, that only the limit comes from UAX #15, and that UAX #15 inserts U+034F instead |
| a/N3 | `build(parse(header))` was promised without limits; a C1 control (legal obs-text for strict parsing) or a non-token type is refused | The promise is qualified in the `build` docstring, the GUIDE and both CHANGELOG entries |
| c/N1 | A `str` subclass overriding `isascii` skipped the first NFKC pass of `safe_filename`, so full-width slashes became separators after the split | `_unicode.normalize` works on a plain copy (`str.__str__`); `build` copies its type, names and values the same way, so an overridden `__iter__` cannot hide a control character either. Tests: `tests/test_mark_runs.py`; CHANGELOG Changed |
| c/N2 | A non-`str` parameter name in a `ContentDisposition` gave `ContentDispositionError` or an internal `TypeError` | `build` raises `TypeError: parameter names must be str, not ...`; tests in `tests/test_build_params.py` for `None`, `1` and `b"x"`; docstring and CHANGELOG |
| e/G1 | NFKD counting of mark runs not pinned (N16) | `safe_filename("a¨" + 29 x U+0301 + U+0316)` pinned: U+0316 is the dropped 31st mark |
| e/G2 | Which characters count as non-starters not pinned (N17) | A run of 40 U+093F (spacing mark, class 0) is kept whole |
| e/G3 | Lower-casing a `ContentDisposition` type before the token check not caught (N28) | Kelvin-sign type and parameter name of a `ContentDisposition` are refused |

Mutants re-run on this PC, each alone, against `tests/test_mark_runs.py` and
`tests/test_build_params.py`: N16, N17 and N28 are killed, and so are removing the plain
copy in `normalize` and removing the name type check.

Gates on Elena's PC (Python 3.14.2) from a clone of 04a8fb7, each on its own:
`ruff format --check .`, `ruff check .`, `mypy --strict src`, `mypy --strict src tests`
and `pytest` all exit 0 (582 passed, 71 skipped without fetched files). With the fetched
sources, Node.js, werkzeug, aiohttp, multipart, the 0.2.1 oracle, `CONTENTDISP_E2E=1`
and `CONTENTDISP_E2E_PYPI=1`: 653 passed, no skip.

Re-verification of round 2 by the same lenses: done in round 3.

### Round 3 (lenses a and e at dc988e8)

Lens a re-checked a/N1 and a/N2 (fixed) and a/N3 (in part, see a/N4). Lens e re-ran its
own mutation round (35 mutants on the laptop, Python 3.14.6): the round 2 survivors N16,
N17, N28 and N28b are killed; of the 11 new survivors, U3, U8, B7 and B14 are shown
equivalent by the lens and the other 7 are e/F1 to e/F3. None is disputed. The contract
test for the one behaviour bug (a/N5) was added first and failed on dc988e8.

| Id | Finding | What changed |
| --- | --- | --- |
| a/N4 | The docs named two kinds of parsed header `build` cannot write again; a lone surrogate (taken as obs-text when a `str` is parsed, even strictly) is a third | The GUIDE, the `build` docstring and both CHANGELOG entries list the lone surrogate as the third kind. Behaviour unchanged: strict parsing still accepts it, as the GUIDE says every `str` character above U+00FF is obs-text |
| a/N5 | `safe_filename` returned a `str` subclass given as `default` unchanged, against the CHANGELOG promise of a plain `str` | `default` is copied with `str.__str__`, so the result is always a plain `str`. Docstring, GUIDE and the CHANGELOG entry say so. Test: `tests/test_str_subclasses.py::test_the_default_comes_back_as_a_plain_str` (also with a subclass overriding `__str__`) |
| e/F1 | No test pinned the plain copy of a parameter name in `build` (B2) | A name overriding `__iter__` that hides CR LF is refused |
| e/F2 | No test pinned the plain copy of the type in `build` (B1) | A type overriding `strip` and `__iter__` is refused, given as a `str` and as `ContentDisposition.type` |
| e/F3 | No test pinned `str.__str__(x)` over `str(x)` (U4, S1, B8, B9, B10) | A subclass overriding `__str__` is checked and written by its real characters in `safe_filename` (name and `default`) and in the type, a name and a value of `build` |

New tests are in `tests/test_str_subclasses.py`. Mutants re-run on this PC, each alone,
against that file: B1, B2, B8, B9, B10 and U4 are killed, and so are removing the new
`default` copy and replacing it with `str(default)`.

Gates on Elena's PC (Python 3.14.2) from a clone of b0c822f, each on its own:
`ruff format --check .`, `ruff check .`, `mypy --strict src`, `mypy --strict src tests`
and `pytest` all exit 0 (592 passed, 71 skipped without fetched files).

Re-verification of round 3 by the same lenses: done in round 4.

### Round 4 (lens e at 74d2c55)

Lens e re-checked e/F1 to e/F3 (fixed: B1, B2, B8, B9, B10, U4 and S1 are killed) and ran
26 mutants (19 new probes and the 7 re-checks) on Elena's PC (Python 3.14.2) and on this
PC: 22 killed, B12 shown equivalent, three survivors (e/N1 to e/N3). None is disputed. All
three are missing tests, not behaviour bugs: the code already uses the real characters, so
the new tests pass on 74d2c55 and fail on the mutants. No behaviour, API or doc change.

| Id | Finding | What changed |
| --- | --- | --- |
| e/N1 | No test pinned that `build` writes a parameter name from its plain copy (B13: `lower` called on the subclass) | A name whose real value is `Size` but whose `lower` returns text with CR LF is written as `size` |
| e/N2 | No test pinned that `build` writes the type from its plain copy when the real value is valid (B15: `strip().lower()` on the subclass) | A type whose real value is ` Inline ` but whose `strip` and `lower` return CR LF text is written as `inline`, given as a `str` and as `ContentDisposition.type` |
| e/N3 | No test pinned that `default` comes back unchanged when it holds whitespace or controls (D5: `default` stripped) | For `None`, `..` and `/`, the defaults `" dl "`, a tab and LF around `dl`, and NUL with U+202E around `dl` come back exactly |

New tests are in `tests/test_str_subclasses.py` (commit 6bd7c4b). Mutants re-run on this PC,
each alone, against that file: B13, B15 and D5 each fail at least one new test, and the
file passes on the unmutated code.

Gates on the laptop (Python 3.14.6) from a clone of 6bd7c4b, each on its own:
`ruff format --check .`, `ruff check .`, `mypy --strict src`, `mypy --strict src tests`
and `pytest` all exit 0 (604 passed, 71 skipped without fetched files). The pytest
`--basetemp` must sit outside the scanned tree (a dot folder or another folder): placed in
a plain subfolder of the clone, the files that the Windows names test creates are read by
the docs tree scan, which then reports their invisible characters.

Re-verification of round 4 by the same lens: done in round 5.

### Round 5 (lens e at 10ed0f3)

Lens e re-checked e/N1 to e/N3 (fixed: B13, B15 and D5 are killed) and ran 24 mutants (21
new probes and the 3 re-checks), each alone on the full suite, on the laptop (Python 3.14)
and on Elena's PC (Python 3.14.2) with the fetched sources: 19 killed, 5 survivors (e/N4 to
e/N8), none equivalent. None is disputed. As in round 4, all five are missing tests, not
behaviour bugs: the code already judges names and the type by their plain copies and
returns `default` as given, so the new tests pass on 10ed0f3 and fail on the mutants. No
behaviour, API or doc change.

| Id | Finding | What changed |
| --- | --- | --- |
| e/N4 | No test pinned that duplicate names are judged by their real characters (P3: the seen set built from `lower` called on the subclass) | Names whose `lower` and `strip` return `x`: `a` and `b` are both written, `A` and `a` are refused as given more than once |
| e/N5 | No test pinned that the extended-name refusal reads the real characters (P5: `is_ext_name` on the subclass's `lower`) | A name whose real value is `filename*` but whose `lower` and `strip` return `x` is refused |
| e/N6 | No test pinned that the form-data decision uses the real type (P8: `strip().lower()` on the subclass) | A real `inline` type whose `strip` and `lower` claim `form-data` still refuses CR LF in a value; a real `form-data` type whose methods claim `inline` is written exactly as plain `form-data`; both given as a `str` and as `ContentDisposition.type` |
| e/N7 | No test used a `default` that NFKC changes (D7: `default` normalised) | For `None`, `..` and `/`, full-width `dl` and `U+FB01` + `le` come back exactly |
| e/N8 | No test used an empty `default` (D13: `default or "download"`) | For `None`, `..` and `/`, `default=""` gives `""` |

New tests are in `tests/test_str_subclasses.py` (commit 93099af). Mutants re-run on this
PC, each alone, against that file: P3, P5, P8, D7 and D13 each fail at least one new test,
and the file passes on the unmutated code.

Gates on the laptop (Python 3.14.6) from a clone of 4424d12, each on its own, with the
fetched sources, Node.js, werkzeug, aiohttp, multipart, the 0.2.1 oracle,
`CONTENTDISP_E2E=1` and `CONTENTDISP_E2E_PYPI=1`: `ruff format --check .`,
`ruff check .`, `mypy --strict src`, `mypy --strict src tests` and `pytest` all exit 0
(688 passed, no skip).

Re-verification of round 5 by the same lens: done in round 6.

### Round 6 (lenses a, b, c, d and e at 8d94bf4)

All five lenses ran again on a fresh view of the branch. Lens a re-checked its earlier
findings (fixed) and ran every doctest, README and GUIDE example; lens b re-derived the
tc2231 responses, the RFC 6266 and RFC 8187 examples, Chromium's expectations and an
independent ABNF oracle over 1.6 million headers without a mismatch; lens c fuzzed about
80,000 strict-valid headers and 176,000 builds and timed 45 hostile shapes up to 1.6 MB
(all linear); lens d built and installed the wheel and the sdist; lens e ran its own
mutation round. None of the findings is disputed. Contract tests for the behaviour bugs
(b/F1, b/F2, b/F3, c/F1, c/F2) were added first and failed on 8d94bf4: 34 test cases
in `tests/test_ext_positions.py`, `tests/test_hostile_types.py` and
`tests/test_positions.py`. The fixes are in 1be185c.

| Id | Finding | What changed |
| --- | --- | --- |
| a/A1 | `build(parse(header))` refuses a name ending in `*` (`a**=UTF-8''x` parses to `a*`), a fourth kind the docs did not list | Documented as the fourth kind in the GUIDE, the `build` docstring and both CHANGELOG entries; behaviour unchanged (`build` never writes an extended name). Test: `tests/test_build_params.py::test_a_parsed_name_ending_in_a_star_is_refused` |
| a/A2 | The 30-mark cut was described as applying to combining marks; it counts non-starters | GUIDE step 1, the `safe_filename` docstring and the CHANGELOG say non-starters (a non-zero canonical combining class); the GUIDE names U+20DD and U+093F as class 0 marks that are never cut (U+093F already pinned by `tests/test_mark_runs.py`) |
| a/A3 | A CHANGELOG bullet claimed 0.2.1 let an `isascii` or `__iter__` override skip normalisation | Clause removed; the bullet keeps the `__iter__` control character in `build` and the plain `str` default, both checked against the 0.2.1 wheel |
| b/F1 | A CR, LF or NUL anywhere was reported before an earlier grammar error | Strict parsing reads the grammar first and treats CR, LF and NUL as ordinary invalid characters; when one of them is the first offending character the message still names it. 60,000 seeded headers with CR, LF or NUL inserted: strict parsing never accepts one and never points past the first |
| b/F2 | A malformed extended value was reported at the start of the value | The position is the first character the RFC 8187 grammar cannot take (charset, delimiter, language, value character or the broken pct-encoding). Two documented exceptions point at a start: octets invalid in their charset (the start of the value) and a language part that is not a well-formed tag (its first character). GUIDE, `parse` and `ContentDispositionError` docstrings, README; the GUIDE example now prints offset 30 |
| b/F3 | ISO-8859-1 C1 octets were invalid but C0 and DEL decoded | 0x00 to 0x1F and 0x7F to 0x9F are all invalid in an ISO-8859-1 extended value (no graphic character in ISO/IEC 8859-1): strict parsing raises, lenient parsing ignores the parameter. The regex oracle in `tests/test_oracle.py` follows; GUIDE and CHANGELOG Changed (0.2.1 decoded `%00` to NUL, checked) |
| b/F4 | README: the `email` package does not always keep whichever comes first | Reworded: `Message.get_filename` always returns the plain `filename`, `EmailMessage` keeps whichever comes first (both checked on CPython 3.13.2) |
| c/F1 | `parse` used `str` and `bytes` subclasses as given (an overridden `replace` let raw CR LF through; an odd `decode` raised `AttributeError`) | `parse` works on plain copies (`str.__str__`, `bytes.decode`). CHANGELOG Fixed (both checked on the 0.2.1 wheel) |
| c/F2 | A metaclass `__name__` property made every wrong-type path raise its own error | `type_name` reads the name through the descriptor of `type` itself; `parse`, `build`, `safe_filename` and `ContentDisposition` give the documented `TypeError`. CHANGELOG Fixed |
| d/F1 | The linear-time test failed once under foreign CPU load | Small and large inputs are timed in turns, the best of three kept, and a slow-looking round is measured again (up to four rounds); a quadratic cost fails every round |
| e/F1-X10 | No test pinned the RFC 8187 mime-charset class (X10: `.` allowed) | Strict parsing of `utf.8`, `utf/8`, `utf:8`, `utf(8`, `utf@8` and `utf 8` raises at the offending character; a well-formed unknown charset (`koi8-r`) is ignored |
| e/F2-B08 | No test pinned the form-data decision for another case or surrounding spaces (B08) | `Form-Data`, ` form-data`, `form-data `, a tab-wrapped `FORM-DATA` and `ContentDisposition("FORM-DATA")` build exactly like `form-data`, with no `filename*` |
| e/F3-P17 | Only an opt-in test pinned that a backslash outside quotes is ordinary (P17) | Always-on lenient tests: `filename=C:\dir\;size=3` and two others split at the `;` |

Mutants re-run on this PC, each alone, on the new tests: X10, B08 and P17 are killed, and so
is a changed refusal message for an extended name. CHANGELOG claims added this round were
checked against the PyPI 0.2.1 wheel (`replace` override, odd `decode`, metaclass name,
`%00` in ISO-8859-1).

Gates: see Gates (1be185c, 749 passed, no skip).

Re-verification of round 6 by the same lenses: done in round 7 below.

### Round 7 (lenses a, b, c and e at 4cf885f)

Lenses a, b, c and e re-checked every round 6 finding and found them fixed (lens d had
none). Lens a ran every README and GUIDE example, the doctests and 38 probes; lens b ran
48 hand probes and a seeded fuzz of 6000 headers against its own grammar oracle; lens c
compared 18,548 positions with its oracle and fuzzed 30,000 headers; lens e ran its own
mutation round. None of the findings is disputed. Contract tests were added first and
failed on 4cf885f (46 test cases in `tests/test_ext_controls.py` and
`tests/test_ext_positions.py`, the ISO-8859-1 ones also for the new message); the pins for the surviving mutants were checked by
running each mutant again on this PC. The fixes are in 13fe189.

| Id | Finding | What changed |
| --- | --- | --- |
| a/N1 | The `ContentDispositionError` docstring said both exceptions point at the start of a value; the tag error points at the start of the tag | The docstring says "the start of a value or of its language tag" and refers to the GUIDE, which lists both |
| a/N2, c/G1 | ISO-8859-1 control octets were refused, but the same controls in UTF-8 decoded, so lenient parsing could return a raw CR LF and strict parsing a NUL | Decoded text holding a control other than HTAB (U+0000 to U+0008, U+000A to U+001F, U+007F to U+009F) is invalid in both charsets: strict parsing raises `control character in extended value` at the start of the value, lenient parsing ignores the parameter. HTAB stays, as a quoted-string and `build` take it (refusing it broke `build`/`parse` round trips of a value with a tab, which `tests/test_fuzz.py` caught); 0.2.1 decoded `%09` in both charsets too (checked on the wheel). `parse` docstring, GUIDE (strict and lenient lists), CHANGELOG Changed, regex oracle in `tests/test_oracle.py`. Tests: `tests/test_ext_controls.py` |
| b/N1 | A malformed language tag followed by a later grammar error was reported at the later error | When the RFC 8187 grammar fails and strict parsing finds a language part closed by its quote that is not a well-formed tag and starts before the first offending character, the error is the tag error at its start. Four reviewer cases pinned in `tests/test_ext_positions.py` (the fourth starts at 33: the reviewer's 34 counted one character too many) plus a control case with a valid tag |
| e/N1-R16-R18 | `{`, `}` and `` ` `` in a charset were not pinned | `test_a_well_formed_unknown_charset_is_ignored` covers ``a!#$%&+-^_`{}~z``, `x{y}`, `` x`y `` and `x^y` in both modes; R16 and R18 are killed |
| e/N2-R24 | A broken pct-encoding with a lowercase first hex digit was not pinned | `%aZ` (31) and `%e` (31) added to the position cases; R24 is killed |
| e/N3-R02 | The 40-character cut of a class name was not pinned at its boundary | A 40-character class name is shown whole and a 41-character one as 37 characters and `...`, for `parse` and `build`; R02 is killed |

Mutants re-run on this PC, each alone: R16, R18, R24, R02, the tag check turned off, and
the control class without LF or with HTAB are all killed.

Gates: see Gates (13fe189, 800 passed, no skip).

Re-verification of round 7 by the same lenses: pending.

## Independent review (item 16)

Pending.
