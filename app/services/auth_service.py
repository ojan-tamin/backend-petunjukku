import json
import uuid
from urllib import error, parse, request

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.schemas.auth import UserCreate, UserLogin


class SupabaseAuthError(Exception):
    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def _ensure_supabase_config() -> None:
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise SupabaseAuthError(
            "Supabase Auth belum dikonfigurasi. Isi SUPABASE_URL dan SUPABASE_ANON_KEY.",
            status_code=500,
        )


def _supabase_headers(access_token: str | None = None) -> dict[str, str]:
    headers = {
        "apikey": settings.supabase_anon_key,
        "Content-Type": "application/json",
    }
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    return headers


def _supabase_request(
    method: str,
    path: str,
    payload: dict | None = None,
    access_token: str | None = None,
) -> dict:
    _ensure_supabase_config()

    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/{path.lstrip('/')}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers=_supabase_headers(access_token),
        method=method,
    )

    try:
        with request.urlopen(req) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        detail = "Supabase Auth request failed"

        if raw:
            try:
                payload = json.loads(raw)
                detail = (
                    payload.get("msg")
                    or payload.get("error_description")
                    or payload.get("error")
                    or payload.get("message")
                    or detail
                )
            except json.JSONDecodeError:
                detail = raw

        raise SupabaseAuthError(detail, status_code=exc.code) from exc
    except error.URLError as exc:
        raise SupabaseAuthError(
            "Tidak bisa terhubung ke Supabase Auth.",
            status_code=502,
        ) from exc


def sign_up_user(user_in: UserCreate) -> dict:
    payload = {
        "email": user_in.email,
        "password": user_in.password,
        "data": {
            "full_name": user_in.full_name,
            "school_name": user_in.school_name,
            "role": "teacher",
        },
    }
    return _supabase_request("POST", "signup", payload=payload)


def sign_in_user(user_in: UserLogin) -> dict:
    query = parse.urlencode({"grant_type": "password"})
    payload = {
        "email": user_in.email,
        "password": user_in.password,
    }
    return _supabase_request("POST", f"token?{query}", payload=payload)


def get_supabase_user(access_token: str) -> dict:
    return _supabase_request("GET", "user", access_token=access_token)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: str | uuid.UUID) -> User | None:
    parsed_id = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
    return db.query(User).filter(User.id == parsed_id).first()


def sync_user_profile(
    db: Session,
    auth_user: dict,
    fallback_profile: UserCreate | None = None,
) -> User:
    auth_user_id = auth_user.get("id")
    auth_email = auth_user.get("email")

    if not auth_user_id or not auth_email:
        raise SupabaseAuthError(
            "Supabase Auth tidak mengembalikan id/email user yang valid.",
            status_code=502,
        )

    user_metadata = auth_user.get("user_metadata") or {}
    existing_user = get_user_by_id(db, auth_user_id)

    if not existing_user:
        email_match = get_user_by_email(db, auth_email)
        if email_match and str(email_match.id) != str(auth_user_id):
            raise SupabaseAuthError(
                "Email sudah ada di profile lokal dengan id berbeda. Migrasikan data user lama dulu sebelum memakai Supabase Auth.",
                status_code=409,
            )

        existing_user = User(id=uuid.UUID(str(auth_user_id)))
        db.add(existing_user)

    existing_user.email = auth_email
    existing_user.full_name = (
        user_metadata.get("full_name")
        or (fallback_profile.full_name if fallback_profile else None)
        or existing_user.full_name
        or auth_email
    )
    existing_user.school_name = (
        user_metadata.get("school_name")
        if "school_name" in user_metadata
        else (
            fallback_profile.school_name
            if fallback_profile is not None
            else existing_user.school_name
        )
    )
    existing_user.role = (
        user_metadata.get("role")
        or existing_user.role
        or "teacher"
    )

    db.commit()
    db.refresh(existing_user)
    return existing_user
