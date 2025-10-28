"""
Minimal compatibility shim for the removed/absent stdlib `cgi` module.

This file only exists to allow code that does `import cgi` (Django's
`django.http.request` does this at import time) to succeed when the
standard-library `cgi` module is not available in the running Python.

The shim implements very small, well-documented pieces of the public
interface that are commonly used (`parse_header`, a minimal
`FieldStorage` placeholder and `parse_multipart` stub). It intentionally
does not try to be a full replacement for the stdlib `cgi` module.

If the real stdlib `cgi` becomes available, this shim will not be used
because local imports take precedence; the shim is only active when the
stdlib module is missing.

Notes:
- This is a low-risk, minimal change intended to restore imports.
- If your application uses file uploads or multipart parsing, prefer to
  migrate to `django`'s request parsing or install a proper multipart
  library; the shim's multipart support is intentionally limited.
"""

from typing import Tuple, Dict, Any

__all__ = ["parse_header", "parse_multipart", "FieldStorage"]


def parse_header(line: str) -> Tuple[str, Dict[str, str]]:
    """Parse a Content-Type like header into (value, params) similar to
    cgi.parse_header. This is a minimal implementation and handles the
    most common form: 'type/subtype; param=value; ...'.
    """
    if not line:
        return "", {}
    parts = [p.strip() for p in line.split(";")]
    value = parts[0]
    params: Dict[str, str] = {}
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            v = v.strip()
            if v.startswith('"') and v.endswith('"'):
                v = v[1:-1]
            params[k.lower()] = v
    return value, params


def parse_multipart(fp, pdict: Dict[str, Any]):
    """A placeholder for cgi.parse_multipart.

    Full multipart parsing is non-trivial. This stub raises
    NotImplementedError to make it explicit that the shim does not
    implement multipart parsing.
    """
    raise NotImplementedError(
        "parse_multipart() is not implemented in the cgi shim. "
        "Install or use a supported multipart parser if your app needs it."
    )


class FieldStorage:
    """Very small placeholder for cgi.FieldStorage.

    This placeholder satisfies imports and basic attribute access that
    may occur at import time. It does not parse form data. If code
    attempts to use FieldStorage to actually parse request data, it
    will get predictable but limited behavior.
    """

    def __init__(self, fp=None, environ=None, keep_blank_values=False, strict_parsing=False):
        self.fp = fp
        self.environ = environ
        self.keep_blank_values = keep_blank_values
        self.strict_parsing = strict_parsing
        # Common attributes that some callers access
        self.value = None
        self.name = None
        self.filename = None
        self.file = None

    def __bool__(self):
        # Behave like an empty storage by default
        return False

    def getvalue(self, name, default=None):
        return default

    # Provide mapping-like methods used by some code paths
    def keys(self):
        return []

    def __iter__(self):
        return iter(())

    def __getitem__(self, key):
        raise KeyError(key)
