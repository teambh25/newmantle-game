from fastapi import Depends, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials

# from app.common.config import configs
from app.common.exceptions import AuthenticationFailed

security = HTTPBasic()

async def authenticate_admin(req: Request, credentials: HTTPBasicCredentials = Depends(security)):
    admin_id = req.app.state.configs.admin_id
    admin_pw = req.app.state.configs.admin_pw
    if credentials.username == admin_id and credentials.password == admin_pw:
        return True
    else:
        raise AuthenticationFailed(msg='Incorrect admin id/pw')