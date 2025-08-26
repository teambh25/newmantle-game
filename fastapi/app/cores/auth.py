from fastapi import Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.exceptions import AuthenticationFailed
from app.cores.config import configs

security = HTTPBasic()

async def authenticate_admin(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username == configs.admin_id and credentials.password == configs.admin_pw:
        return True
    else:
        raise AuthenticationFailed(msg="Incorrect admin id/pw")