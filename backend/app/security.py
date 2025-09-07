from __future__ import annotations
import json
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
import httpx
from .config import settings

http_bearer = HTTPBearer(auto_error=False)
_jwks_cache: Optional[dict] = None

async def _get_jwks():
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache
    if not settings.auth0_domain:
        return None
    url = f"https://{settings.auth0_domain}/.well-known/jwks.json"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        return _jwks_cache

async def verify_jwt(creds: HTTPAuthorizationCredentials = Depends(http_bearer)):
    if settings.auth_disabled:
        return None
    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    token = creds.credentials
    jwks = await _get_jwks()
    if not jwks:
        raise HTTPException(status_code=500, detail="JWKS unavailable")
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")
    key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if not key:
        raise HTTPException(status_code=401, detail="Invalid token header")
    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=[key.get("alg", "RS256")],
            audience=settings.auth0_audience,
            issuer=f"https://{settings.auth0_domain}/",
        )
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token invalid: {e}")

