import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
PASSWORD_LETTER_PATTERN = re.compile(r"[A-Za-z]")
PASSWORD_DIGIT_PATTERN = re.compile(r"\d")


def validate_password_strength(value: str) -> str:
    if len(value) < 8:
        raise ValueError("password must be at least 8 characters")
    if not PASSWORD_LETTER_PATTERN.search(value):
        raise ValueError("password must contain at least one letter")
    if not PASSWORD_DIGIT_PATTERN.search(value):
        raise ValueError("password must contain at least one digit")
    return value


class RegisterRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    username: str = Field(min_length=2, max_length=60)
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=8, max_length=200)

    @field_validator("username")
    @classmethod
    def _validate_username(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("username must be at least 2 characters")
        for char in normalized:
            if char in {"_", ".", "-"} or char.isalnum():
                continue
            raise ValueError("username may only contain letters, numbers, underscore, dot, or hyphen")
        return normalized

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        normalized = value.strip()
        if not EMAIL_PATTERN.match(normalized):
            raise ValueError("invalid email address")
        return normalized

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        return validate_password_strength(value)


class LoginRequest(BaseModel):
    login: str = Field(min_length=2, max_length=200)
    password: str = Field(min_length=1, max_length=200)


class AuthUserRead(BaseModel):
    id: int
    display_name: str
    username: str | None = None
    email: str | None = None
    is_active: bool
    is_admin: bool = False
    created_at: datetime
    credit_balance: int = 0


class AuthSessionResponse(BaseModel):
    user: AuthUserRead
