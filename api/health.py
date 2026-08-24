"""Vercel file-route entrypoint for the FastAPI health endpoint.

The Vite deployment uses file-based Python routing. Re-exporting the established
application ensures `/api/health` reaches the same typed FastAPI app as `/api`.
"""

from api.index import app

__all__ = ["app"]
