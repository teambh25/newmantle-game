import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.cores.auth import UserIdentity, get_current_subject
from app.exceptions import AuthenticationFailed

VALID_UUID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


def _creds() -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")


class TestGetUserIdentity:
    @pytest.mark.asyncio
    async def test_returns_guest_when_no_jwt_and_valid_guest_id(self):
        identity = await get_current_subject(None, VALID_UUID)
        assert identity == UserIdentity(id=VALID_UUID, is_guest=True)

    @pytest.mark.asyncio
    async def test_raises_when_neither_jwt_nor_guest_id(self):
        with pytest.raises(AuthenticationFailed):
            await get_current_subject(None, None)

    @pytest.mark.asyncio
    async def test_raises_when_invalid_guest_id(self):
        with pytest.raises(AuthenticationFailed):
            await get_current_subject(None, "not-a-uuid")

    @pytest.mark.asyncio
    async def test_raises_when_both_jwt_and_guest_id_present(self):
        with pytest.raises(AuthenticationFailed):
            await get_current_subject(_creds(), VALID_UUID)

    @pytest.mark.asyncio
    async def test_raises_when_jwt_is_invalid(self):
        # Covers jwt.PyJWTError path. jwt.ExpiredSignatureError requires a real
        # expired token (needs jwt_secret), so it is not tested here.
        with pytest.raises(AuthenticationFailed):
            await get_current_subject(_creds(), None)
