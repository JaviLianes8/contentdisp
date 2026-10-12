"""Build the wheel, install it in a throwaway venv and drive the installed package.

Slow and needs the build backend, so it runs only with CONTENTDISP_E2E=1.
"""

from __future__ import annotations

import os
import subprocess
import sys
import venv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    os.environ.get("CONTENTDISP_E2E") != "1", reason="set CONTENTDISP_E2E=1 to build and install"
)

PROGRAM = r"""
import importlib.metadata, importlib.resources
import contentdisp
from contentdisp import ContentDisposition, build, parse, safe_filename

assert "site-packages" in contentdisp.__file__, contentdisp.__file__
assert importlib.metadata.version("contentdisp") == contentdisp.__version__
assert importlib.resources.files("contentdisp").joinpath("py.typed").is_file()

header = "attachment; filename=\"EURO rates\"; filename*=utf-8''%e2%82%ac%20rates"
assert parse(header, strict=True) == ContentDisposition("attachment", {"filename": "€ rates"})
assert parse(b'attachment; filename="caf\xe9"').filename == "café"
assert parse("attachment; filename=a; filename*=UTF-8'bad").filename == "a"
for bad in ("attachment; filename=a; filename=b", 'attachment; filename="x', "inline; attachment"):
    try:
        parse(bad, strict=True)
    except ValueError:
        pass
    else:
        raise AssertionError(bad)
name = "€ \"quoted\" \\ 100%41.txt"
assert parse(build("attachment", name), strict=True).filename == name
assert "*" not in build("form-data", "é.txt", name="f")
try:
    build("attachment", "a\r\nSet-Cookie: x=1")
except ValueError:
    pass
else:
    raise AssertionError("header injection")
traversal = parse("attachment; filename*=UTF-8''..%2F..%2Fetc%2Fpasswd").filename
assert safe_filename(traversal) == "passwd"
assert safe_filename("CON") == "_CON"
print("e2e ok")
"""


def _run(*cmd: str | Path, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(c) for c in cmd], cwd=cwd, capture_output=True, text=True, check=False
    )


def test_installed_wheel_end_to_end(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    built = _run(sys.executable, "-m", "build", "--wheel", "--outdir", dist, ROOT)
    assert built.returncode == 0, built.stderr
    (wheel,) = dist.glob("contentdisp-*.whl")

    env_dir = tmp_path / "venv"
    venv.create(env_dir, with_pip=True)
    bindir = env_dir / ("Scripts" if sys.platform == "win32" else "bin")
    python = bindir / "python"
    installed = _run(python, "-m", "pip", "install", "-q", wheel)
    assert installed.returncode == 0, installed.stderr

    # Run from an empty folder so the source tree cannot shadow the install.
    work = tmp_path / "work"
    work.mkdir()
    result = _run(python, "-I", "-c", PROGRAM, cwd=work)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "e2e ok"
