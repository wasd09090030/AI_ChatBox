"""
Backward-compatible story router import.

The actual implementations are now split under `api.v2.story.*`
to keep each module focused and avoid large route files.
"""

from .story import router

__all__ = ["router"]
