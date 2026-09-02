"""Authentication routes: register, login (OAuth2 password flow), me."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from ..container import Container
from ..deps import container, get_current_user
from ..schemas.auth import RegisterIn, TokenOut, UserOut
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _to_user_out(u: dict) -> UserOut:
    return UserOut(
        id=u["id"], name=u["name"], email=u["email"], role=u["role"],
        status=u["status"], joined=u["joined"], last_seen=u["last_seen"],
    )


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, c: Container = Depends(container)) -> TokenOut:
    if c.users.get_by_email(body.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email is already registered.")
    today = date.today().isoformat()
    user = c.users.create({
        "name": body.name,
        "email": body.email,
        "role": "USER",
        "status": "ACTIVE",
        "joined": today,
        "last_seen": today,
        "password_hash": hash_password(body.password),
    })
    token = create_access_token(user_id=user["id"], role=user["role"])
    return TokenOut(access_token=token)


@router.post("/login", response_model=TokenOut)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    c: Container = Depends(container),
) -> TokenOut:
    # OAuth2 form uses "username"; we treat it as the email.
    user = c.users.get_by_email(form.username)
    if not user or not verify_password(form.password, user["password_hash"]):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    c.users.touch_last_seen(user["id"], date.today().isoformat())
    token = create_access_token(user_id=user["id"], role=user["role"])
    return TokenOut(access_token=token)


@router.get("/me", response_model=UserOut)
def me(user: dict = Depends(get_current_user)) -> UserOut:
    return _to_user_out(user)
