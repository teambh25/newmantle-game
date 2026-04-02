import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, Header
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
)

from app.cores.config import configs
from app.exceptions import AuthenticationFailed


@dataclass(frozen=True)
class UserIdentity:
    id: str
    is_guest: bool


# Admin HTTP Basic Auth
security = HTTPBasic()


async def authenticate_admin(credentials: HTTPBasicCredentials = Depends(security)):
    if (
        credentials.username == configs.admin_id
        and credentials.password == configs.admin_pw
    ):
        return True
    else:
        raise AuthenticationFailed(msg="Incorrect admin id/pw")


# Supabase JWT Auth
bearer_scheme = HTTPBearer(auto_error=False)


def _verify_supabase_jwt(token: str) -> dict:
    """Verify a Supabase JWT and return the payload. Raises AuthenticationFailed on failure."""
    try:
        return jwt.decode(
            token,
            configs.jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
            issuer=f"{configs.jwt_issuer}/auth/v1",
        )
    except jwt.ExpiredSignatureError:
        raise AuthenticationFailed(msg="Token has expired. Please log in again")
    except jwt.PyJWTError:
        raise AuthenticationFailed(msg="Invalid token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    """Return user_id from a valid token. Raises 401 if missing or invalid."""
    if credentials is None:
        raise AuthenticationFailed(msg="Authorization header required")
    payload = _verify_supabase_jwt(credentials.credentials)
    return payload["sub"]


async def get_current_subject(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_guest_id: str | None = Header(None),
) -> UserIdentity:
    """Return UserIdentity from JWT or X-Guest-Id header. Raises 401 if neither is present or both are present."""
    if credentials is not None and x_guest_id is not None:
        raise AuthenticationFailed(
            msg="Provide either Authorization or X-Guest-Id, not both"
        )

    if credentials is not None:
        payload = _verify_supabase_jwt(credentials.credentials)
        return UserIdentity(id=payload["sub"], is_guest=False)

    if x_guest_id is not None:
        try:
            uuid.UUID(x_guest_id)
        except ValueError:
            raise AuthenticationFailed(msg="Invalid guest ID format")
        return UserIdentity(id=x_guest_id, is_guest=True)

    raise AuthenticationFailed(msg="Authorization header or X-Guest-Id required")
