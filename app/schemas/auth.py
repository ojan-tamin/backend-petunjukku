from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    full_name: str = Field(..., max_length=150)
    email: EmailStr
    password: str = Field(..., min_length=6)
    school_name: str | None = Field(default=None, max_length=200)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: UUID
    full_name: str
    email: EmailStr
    school_name: str | None
    role: str

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    expires_in: int | None = None
    token_type: str = "bearer"
