from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.schemas.auth import TokenResponse, UserCreate, UserLogin, UserResponse
from app.services.auth_service import (
    SupabaseAuthError,
    sign_in_user,
    sign_up_user,
    sync_user_profile,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    try:
        auth_response = sign_up_user(user_in)
        auth_user = auth_response.get("user")

        if not auth_user:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Supabase Auth tidak mengembalikan user baru.",
            )

        return sync_user_profile(db, auth_user, fallback_profile=user_in)
    except SupabaseAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/login", response_model=TokenResponse)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    try:
        auth_response = sign_in_user(user_in)
        auth_user = auth_response.get("user")
        access_token = auth_response.get("access_token")

        if not auth_user or not access_token:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Supabase Auth tidak mengembalikan session login yang valid.",
            )

        sync_user_profile(db, auth_user)

        return TokenResponse(
            access_token=access_token,
            refresh_token=auth_response.get("refresh_token"),
            expires_in=auth_response.get("expires_in"),
            token_type=auth_response.get("token_type", "bearer"),
        )
    except SupabaseAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/me", response_model=UserResponse)
def get_me(current_user=Depends(get_current_user)):
    return current_user
