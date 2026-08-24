"""Vercel file-route entrypoint for typed deterministic research.

The report contract remains implemented centrally in `api.index`; this module
only maps Vercel's `/api/research` file route to that same application.
"""

from api.index import app

__all__ = ["app"]
