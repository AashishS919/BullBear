"""FastAPI dependencies: container access, current-user resolution, RBAC guards."""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from .container import Container, get_container
from .security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def container() -> Container:
    return get_container()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    c: Container = Depends(container),
) -> dict:
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise _CREDENTIALS_EXC
    except jwt.PyJWTError:
        raise _CREDENTIALS_EXC

    user = c.users.get_by_id(user_id)
    if user is None:
        raise _CREDENTIALS_EXC
    if user.get("status") == "SUSPENDED":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account suspended")
    return user


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "ADMIN":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin privileges required")
    return user
