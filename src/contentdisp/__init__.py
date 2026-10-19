"""Parse and build HTTP Content-Disposition headers per RFC 6266 and RFC 8187."""

from ._build import build
from ._errors import ContentDispositionError
from ._model import ContentDisposition
from ._parse import parse
from ._safe import safe_filename

__version__ = "1.0.0"

# The public classes show and pickle as contentdisp.<Name>, so a pickle never depends on
# the private module that defines them (pickles made by 0.2.1 still load).
ContentDisposition.__module__ = __name__
ContentDispositionError.__module__ = __name__

__all__ = ["ContentDisposition", "ContentDispositionError", "build", "parse", "safe_filename"]
