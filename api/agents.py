"""Vercel file-route entrypoint for AgentOS discovery.

This re-exports the existing FastAPI application; it does not create a second
AgentOS instance or alter the provider architecture.
"""

from api.index import app

__all__ = ["app"]
