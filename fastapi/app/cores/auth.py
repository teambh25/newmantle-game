import jwt
from fastapi import Depends
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
)

from app.cores.config import configs
from app.exceptions import AuthenticationFailed

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


def verify_supabase_jwt(token: str) -> dict:
    """Verify a Supabase JWT and return the payload. Raises AuthenticationFailed on failure."""
    try:
        return jwt.decode(
            token,
            configs.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
            issuer=f"{configs.supabase_url}/auth/v1",
        )
    except jwt.ExpiredSignatureError:
        raise AuthenticationFailed(msg="Token has expired. Please log in again")
    except jwt.PyJWTError:
        raise AuthenticationFailed(msg="Invalid token")


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str | None:
    """Return user_id if token is present and valid, None if absent. Raises 401 if token is invalid."""
    if credentials is None:
        return None
    payload = verify_supabase_jwt(credentials.credentials)
    return payload.get("sub")


async def get_required_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    """Return user_id from a valid token. Raises 401 if missing or invalid."""
    if credentials is None:
        raise AuthenticationFailed(msg="Authorization header required")
    payload = verify_supabase_jwt(credentials.credentials)
    return payload["sub"]
