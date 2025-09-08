"""Auth disabled: this module is kept for compatibility but does nothing."""

from __future__ import annotations
from typing import Any

async def verify_jwt(*args: Any, **kwargs: Any):
    return None

