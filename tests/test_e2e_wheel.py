"""Build the wheel and sdist, inspect them, install the wheel and drive it as a consumer.

Slow and needs the build backend, so it runs only with CONTENTDISP_E2E=1; the upgrade
from the PyPI release also needs CONTENTDISP_E2E_PYPI=1 (network).
"""

from __future__ import annotations

import os
import subprocess
import sys
import tarfile
import venv
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    os.environ.get("CONTENTDISP_E2E") != "1", reason="set CONTENTDISP_E2E=1 to build and install"
)

PROGRAM = r"""
import importlib.metadata, importlib.resources, pickle
import contentdisp
from contentdisp import ContentDisposition, ContentDispositionError, build, parse, safe_filename

assert "site-packages" in contentdisp.__file__, contentdisp.__file__
assert contentdisp.__version__ == importlib.metadata.version("contentdisp") == "1.0.0"
assert sorted(n for n in dir(contentdisp) if not n.startswith("_")) == sorted(contentdisp.__all__)
assert importlib.resources.files("contentdisp").joinpath("py.typed").is_file()
header = "attachment; filename=\"EURO rates\"; filename*=utf-8''%e2%82%ac%20rates"
assert parse(header, strict=True) == ContentDisposition("attachment", {"filename": "€ rates"})
assert pickle.loads(pickle.dumps(parse(header))) == parse(header)
assert repr(ContentDisposition).startswith("<class 'contentdisp.ContentDisposition'")
assert parse(b'attachment; filename="caf\xe9"').filename == "café"
assert parse("attachment; filename=a; filename*=UTF-8'bad").filename == "a"
assert parse("filename=a.txt").filename == "a.txt" and not parse("filename=a.txt").is_attachment
try:
    parse("  attachment filename=a", strict=True)
except ContentDispositionError as error:
    assert error.position == 13 and isinstance(error, ValueError)
    assert pickle.loads(pickle.dumps(error)).position == 13
else:
    raise AssertionError("strict accepted a missing semicolon")
name = "€ \"quoted\" \\ 100%41.txt"
assert parse(build("attachment", name), strict=True).filename == name
assert "*" not in build("form-data", "é.txt", name="f")
try:
    build("attachment", "a\r\nSet-Cookie: x=1")
except ContentDispositionError:
    pass
else:
    raise AssertionError("header injection")
traversal = parse("attachment; filename*=UTF-8''..%2F..%2Fetc%2Fpasswd").filename
assert safe_filename(traversal) == "passwd" and safe_filename("CON") == "_CON"
print("e2e ok")
"""


def _run(*cmd: str | Path, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(c) for c in cmd], cwd=cwd, capture_output=True, text=True, check=False
    )


@pytest.fixture(scope="module")
def dist(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("dist")
    built = _run(sys.executable, "-m", "build", "--outdir", out, ROOT)
    assert built.returncode == 0, built.stderr
    return out


def _venv(folder: Path) -> Path:
    venv.create(folder, with_pip=True)
    return folder / ("Scripts" if sys.platform == "win32" else "bin") / "python"


def _check(python: Path, work: Path) -> None:
    # Run from an empty folder so the source tree cannot shadow the install.
    work.mkdir(exist_ok=True)
    result = _run(python, "-I", "-c", PROGRAM, cwd=work)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "e2e ok"


def test_wheel_contents_and_metadata(dist: Path) -> None:
    (wheel,) = dist.glob("contentdisp-1.0.0-py3-none-any.whl")
    archive = zipfile.ZipFile(wheel)
    names = archive.namelist()
    modules = ["__init__", "_build", "_errors", "_ext_value", "_grammar", "_langtag"]
    modules += ["_model", "_parse", "_safe"]
    package = sorted(n for n in names if n.startswith("contentdisp/"))
    assert package == sorted([f"contentdisp/{m}.py" for m in modules] + ["contentdisp/py.typed"])
    others = {n.split("/", 1)[1] for n in names if not n.startswith("contentdisp/")}
    assert others == {"METADATA", "WHEEL", "RECORD", "licenses/LICENSE"}, others
    metadata = archive.read("contentdisp-1.0.0.dist-info/METADATA").decode("utf-8")
    for line in [
        "Version: 1.0.0",
        "Requires-Python: >=3.10",
        "License-Expression: MIT",
        "Classifier: Development Status :: 5 - Production/Stable",
        "Classifier: Programming Language :: Python :: 3.14",
        "Project-URL: Source, https://github.com/JaviLianes8/contentdisp",
        "Project-URL: Changelog, https://github.com/JaviLianes8/contentdisp/blob/main/CHANGELOG.md",
    ]:
        assert line in metadata.splitlines(), line
    requires = [line for line in metadata.splitlines() if line.startswith("Requires-Dist:")]
    assert requires and all(line.endswith("; extra == 'dev'") for line in requires), requires


def test_sdist_contents(dist: Path) -> None:
    (sdist,) = dist.glob("contentdisp-1.0.0.tar.gz")
    with tarfile.open(sdist) as archive:
        names = {n.split("/", 1)[1] for n in archive.getnames() if "/" in n}
    for present in ("tests/upstream/MANIFEST.json", "scripts/fetch_upstream.py", "GUIDE.md"):
        assert present in names, present
    assert {"LICENSE", "README.md", "CHANGELOG.md", "pyproject.toml", "PKG-INFO"} <= names
    assert {
        "scripts/jshttp_oracle.mjs",
        "tests/test_upgrade.py",
        "src/contentdisp/py.typed",
    } <= names
    upstream = sorted(name for name in names if name.startswith("tests/upstream/"))
    assert upstream == ["tests/upstream/MANIFEST.json"], upstream
    for absent in ("IMPROVEMENTS", "CERT-1.0", ".txt", ".html", ".cc", ".tgz", ".ps1"):
        assert not any(absent in name for name in names), absent
    # hatchling always adds .gitignore; nothing else hidden and no bytecode ships.
    hidden = {name for name in names if name.startswith(".") or "__pycache__" in name}
    assert hidden == {".gitignore"}, hidden


def test_installed_wheel_end_to_end(dist: Path, tmp_path: Path) -> None:
    (wheel,) = dist.glob("contentdisp-*.whl")
    python = _venv(tmp_path / "venv")
    installed = _run(python, "-m", "pip", "install", "-q", wheel)
    assert installed.returncode == 0, installed.stderr
    _check(python, tmp_path / "work")


@pytest.mark.skipif(
    os.environ.get("CONTENTDISP_E2E_PYPI") != "1", reason="set CONTENTDISP_E2E_PYPI=1 to use PyPI"
)
def test_upgrade_in_place_from_the_pypi_release(dist: Path, tmp_path: Path) -> None:
    (wheel,) = dist.glob("contentdisp-*.whl")
    python = _venv(tmp_path / "venv")
    old = _run(python, "-m", "pip", "install", "-q", "contentdisp==0.2.1")
    assert old.returncode == 0, old.stderr
    probe = (
        "import contentdisp as c; p = c.parse; print(c.__version__, p('attachment; filename=a')"
        ".filename, p('filename=b').filename, p('').is_attachment, c.safe_filename('x.pdf'))"
    )
    before = _run(python, "-I", "-c", probe, cwd=tmp_path)
    assert before.stdout.split() == ["0.2.1", "a", "None", "True", "x.pdf"], before.stderr
    upgraded = _run(python, "-m", "pip", "install", "-q", "--upgrade", wheel)
    assert upgraded.returncode == 0, upgraded.stderr
    after = _run(python, "-I", "-c", probe, cwd=tmp_path)
    assert after.stdout.split() == ["1.0.0", "a", "b", "False", "x.pdf"], after.stderr
    _check(python, tmp_path / "work")
