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
- [ ] Five QA lenses report PASS (item 19): rounds 1 and 2 findings fixed, re-verification pending
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

24 mutants over every module with logic, each applied alone to a fresh clone of the
pushed branch on another machine, the full suite run with `-x`. 23 killed at once; M22
(the message cut keeping 43 characters) survived and is killed by the contract added in
b81458e. The table is in [CERT-1.0-MUTANTS.md](https://github.com/JaviLianes8/contentdisp/blob/main/CERT-1.0-MUTANTS.md).

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

At b81458e on another machine from a fresh clone, each command on its own, with the
fetched sources, Node.js, werkzeug, aiohttp, multipart, the 0.2.1 oracle,
`CONTENTDISP_E2E=1` and `CONTENTDISP_E2E_PYPI=1`: `ruff format --check .`,
`ruff check .`, `mypy --strict src`, `mypy --strict src tests` and `pytest` (466 passed,
no skip) all exit 0.

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

Re-verification of round 2 by the same lenses: pending.

## Independent review (item 16)

Pending.
