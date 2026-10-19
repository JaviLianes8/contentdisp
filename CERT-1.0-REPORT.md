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
- [ ] Five QA lenses report PASS (item 19)
- [ ] Independent reviewer reports PASS (item 16)
- [ ] PR and trace guard (item 17); merge and publish left to the maintainer

## Scorecard

| # | Item | Result |
| --- | --- | --- |
| 1 | Public API reviewed for stability | PASS: the five names of 0.2.1 kept with their signatures and parameter names, pinned by `tests/test_contract_api.py`; one name added (`ContentDispositionError`); every behaviour change in the CHANGELOG and the GUIDE, each checked against 0.2.1 |
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
| 17 | PR and trace guard | pending |
| 18 | Contracts bite (mutations) | PASS: 24 author mutants, 23 killed at once, the survivor killed by a contract added in b81458e |
| 19 | Five independent QA lenses | pending |

## API review (item 1)

Kept: `parse(header, *, strict=False)`, `ContentDisposition(type, params)` with
`filename` and `is_attachment`, `build(type, filename=None, **params)` and
`safe_filename(name, *, default="download", max_bytes=255)`, with the parameter names
and defaults of 0.2.1. Added: `ContentDispositionError`, a `ValueError` subclass, so
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
  wheel and sdist; the wheel holds exactly the nine modules, `py.typed`, LICENSE and its
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

Pending.

## Independent review (item 16)

Pending.
