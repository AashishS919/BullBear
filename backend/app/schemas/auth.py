"""Auth request/response schemas with strict validation mirroring the frontend."""
import re

from pydantic import BaseModel, EmailStr, Field, field_validator

from .common import Role, UserStatus

# Strict password: min 8, at least one upper, one lower, one digit (matches Register.jsx)
_PW_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$")


class RegisterIn(BaseModel):
    name: str = Field(min_length=3, max_length=80)
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not _PW_RE.match(v):
            raise ValueError(
                "Password must be at least 8 characters and include an uppercase "
                "letter, a lowercase letter, and a number."
            )
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: Role
    status: UserStatus
    joined: str
    last_seen: str
