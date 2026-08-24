"""Vercel file-route entrypoint for the preserved AgentOS run endpoint.

Vercel maps this nested file to `/api/agents/groq-finance-agent/runs`. The
central FastAPI application continues to own request validation and execution.
"""

from api.index import app

__all__ = ["app"]
