"""Stateless bearer tokens (demo-grade), signed with an HMAC secret from env.

Token = base64url(payload).base64url(hmac_sha256(payload)). Payload carries the
user id and issue time. No third-party JWT dependency.
"""

from __future__ import annotations

import base64
import hmac
import json
import os
import time
from hashlib import sha256
from typing import Optional

from fastapi import Header, HTTPException

import accounts

_SECRET = os.environ.get("AUTH_SECRET", "verdict-dev-secret-change-me").encode()
_TTL = int(os.environ.get("AUTH_TTL_SECONDS", str(60 * 60 * 24 * 7)))  # 7 days


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def make_token(user_id: int) -> str:
    payload = _b64(json.dumps({"uid": user_id, "iat": int(time.time())}).encode())
    sig = _b64(hmac.new(_SECRET, payload.encode(), sha256).digest())
    return f"{payload}.{sig}"


def _decode(token: str) -> Optional[int]:
    try:
        payload, sig = token.split(".")
    except ValueError:
        return None
    expected = _b64(hmac.new(_SECRET, payload.encode(), sha256).digest())
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        data = json.loads(_unb64(payload))
    except (ValueError, json.JSONDecodeError):
        return None
    if int(time.time()) - int(data.get("iat", 0)) > _TTL:
        return None
    return int(data.get("uid"))


def current_user(authorization: str = Header(default="")) -> dict:
    """FastAPI dependency: resolve the bearer token to a user, or 401."""
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    uid = _decode(authorization.split(" ", 1)[1].strip())
    if uid is None:
        raise HTTPException(status_code=401, detail="Session expired — please sign in again.")
    user = accounts.get_user(uid)
    if not user:
        raise HTTPException(status_code=401, detail="Account not found.")
    return user
