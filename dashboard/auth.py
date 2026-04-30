import time
import jwt
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
import config

COOKIE_NAME = "dashboard_token"


def create_token() -> str:
    payload = {"sub": "admin", "exp": time.time() + config.JWT_EXPIRE_HOURS * 3600}
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def verify_token(token: str) -> bool:
    try:
        jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        return True
    except jwt.PyJWTError:
        return False


def get_token_from_request(request: Request) -> str | None:
    return request.cookies.get(COOKIE_NAME)


async def require_auth(request: Request):
    token = get_token_from_request(request)
    if not token or not verify_token(token):
        raise HTTPException(status_code=401, detail="Unauthorized")
