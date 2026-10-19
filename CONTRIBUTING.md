# Contributing

Thanks for taking the time. This project keeps a small, predictable shape.

## Setup

```
pip install -r requirements-dev.txt
```

Some tests compare the library with third-party material that is not committed: the
RFC texts, the tc2231 browser corpus, Chromium's test expectations, the HTML standard,
Microsoft's naming rules and the jshttp npm tarballs, all listed with their URL and
SHA-256 in `tests/upstream/MANIFEST.json`. Fetch them with
`python scripts/fetch_upstream.py`; until then those tests skip. The tests never reach
the network themselves.

Other tests need optional tools and skip without them: Node.js for the jshttp parsers,
werkzeug 3.1.9, aiohttp 3.14.5 and multipart 2.0.1 for the Python oracles,
`CONTENTDISP_V021` (a folder holding the unpacked 0.2.1 wheel) for the upgrade
comparison, and `CONTENTDISP_E2E=1`
(plus `CONTENTDISP_E2E_PYPI=1`) to build the wheel and test the installed package.

## Before you open a pull request

- Keep public API in `src/contentdisp/__init__.py`; internals live in `_`-prefixed modules.
- Add a test for the behaviour you change. Most tests are pure functions; a few touch the
  real system on purpose: `tests/test_windows_names.py` creates files in pytest's
  temporary folder, and the Node.js oracle and the e2e tests run subprocesses in
  temporary folders.
- Run `scripts/check.ps1` (format, lint, types, tests) and make sure it passes.
- One logical change per commit, imperative subject line.

Open an issue first if the change is large or shifts the public API.
