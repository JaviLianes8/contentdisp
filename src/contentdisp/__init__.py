"""Parse and build HTTP Content-Disposition headers, with correct RFC 5987 filename* handling."""

from __future__ import annotations

from ._build import build
from ._model import ContentDisposition
from ._parse import parse

__version__ = "0.1.0"

__all__ = ["ContentDisposition", "build", "parse"]
