"""Parse and build HTTP Content-Disposition headers per RFC 6266 and RFC 8187."""

from __future__ import annotations

from ._build import build
from ._model import ContentDisposition
from ._parse import parse
from ._safe import safe_filename

__version__ = "0.2.0"

__all__ = ["ContentDisposition", "build", "parse", "safe_filename"]
