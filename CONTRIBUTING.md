# Contributing

Thanks for taking the time. This project keeps a small, predictable shape.

## Setup

```
pip install -r requirements-dev.txt
```

The tc2231 browser-corpus tests use a third-party page that is not committed. Fetch it
with `python scripts/fetch_upstream.py`; until then those tests skip.

## Before you open a pull request

- Keep public API in `src/contentdisp/__init__.py`; internals live in `_`-prefixed modules.
- Add a test for the behaviour you change. Tests inject time, disk and network; they
  never touch the real thing.
- Run `scripts/check.ps1` (format, lint, types, tests) and make sure it passes.
- One logical change per commit, imperative subject line.

Open an issue first if the change is large or shifts the public API.
