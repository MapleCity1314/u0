import os
import time
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile, File, Request

from ..core.config import MEDIA_BASE_PATH, MEDIA_DIR, PUBLIC_BASE_URL
from ..core.security import hash_password, verify_password
from ..core.state import issuer, store
from ..models.schemas import (
    ApiResponse,
    AuthResponse,
    InviteCreateRequest,
    InviteResponse,
    LoginRequest,
    ProfileUpdateRequest,
    PasswordUpdateRequest,
    RegisterRequest,
)

router = APIRouter()
def _get_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]


def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
):
    token_value = _get_token(authorization)
    if token_value is None:
        raise HTTPException(status_code=401, detail="missing_token")
    token = issuer.validate(token_value)
    if token is None:
        raise HTTPException(status_code=401, detail="invalid_token")
    user = store.get_user(token.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid_user")
    if user.must_change_password:
        allowed = {
            "/api/auth/me",
            "/api/auth/password",
            "/api/auth/profile",
            "/api/auth/avatar",
        }
        if request.url.path not in allowed:
            raise HTTPException(status_code=403, detail="password_change_required")
    return user


@router.post("/register", response_model=ApiResponse)
def register(req: RegisterRequest):
    if not store.use_invite(req.invite_code):
        raise HTTPException(status_code=400, detail="invalid_invite")
    if store.get_user_by_username(req.username):
        raise HTTPException(status_code=400, detail="username_exists")
    password_hash = hash_password(req.password)
    user = store.create_user(req.username, password_hash, req.name)
    token = issuer.issue(user.id)
    return ApiResponse(
        ok=True,
        data=AuthResponse(
            token=token.value,
            user_id=user.id,
            name=user.name,
            username=user.username,
            avatar_url=user.avatar_url,
            must_change_password=user.must_change_password,
        ).dict(),
    )


@router.post("/login", response_model=ApiResponse)
def login(req: LoginRequest):
    user = store.get_user_by_username(req.username)
    if user is None or not verify_password(user.password_hash, req.password):
        raise HTTPException(status_code=401, detail="invalid_credentials")
    token = issuer.issue(user.id)
    return ApiResponse(
        ok=True,
        data=AuthResponse(
            token=token.value,
            user_id=user.id,
            name=user.name,
            username=user.username,
            avatar_url=user.avatar_url,
            must_change_password=user.must_change_password,
        ).dict(),
    )


@router.get("/me", response_model=ApiResponse)
def me(user=Depends(get_current_user)):
    return ApiResponse(
        ok=True,
        data={
            "user_id": user.id,
            "name": user.name,
            "username": user.username,
            "avatar_url": user.avatar_url,
            "must_change_password": user.must_change_password,
        },
    )


@router.patch("/profile", response_model=ApiResponse)
def update_profile(req: ProfileUpdateRequest, user=Depends(get_current_user)):
    updated = store.update_user(user.id, name=req.name, avatar_url=req.avatar_url)
    if updated is None:
        raise HTTPException(status_code=404, detail="user_not_found")
    return ApiResponse(
        ok=True,
        data={
            "user_id": updated.id,
            "name": updated.name,
            "username": updated.username,
            "avatar_url": updated.avatar_url,
            "must_change_password": updated.must_change_password,
        },
    )


@router.post("/password", response_model=ApiResponse)
def update_password(req: PasswordUpdateRequest, user=Depends(get_current_user)):
    if not verify_password(user.password_hash, req.old_password):
        raise HTTPException(status_code=400, detail="invalid_password")
    new_hash = hash_password(req.new_password)
    updated = store.update_password(user.id, new_hash, False)
    if updated is None:
        raise HTTPException(status_code=404, detail="user_not_found")
    return ApiResponse(
        ok=True,
        data={
            "user_id": updated.id,
            "name": updated.name,
            "username": updated.username,
            "avatar_url": updated.avatar_url,
            "must_change_password": updated.must_change_password,
        },
    )


@router.post("/avatar", response_model=ApiResponse)
async def upload_avatar(file: UploadFile = File(...), user=Depends(get_current_user)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="invalid_image")
    ext = os.path.splitext(file.filename or "")[1].lower() or ".png"
    filename = f"{user.id}_{int(time.time())}_{uuid.uuid4().hex[:6]}{ext}"
    path = os.path.join(MEDIA_DIR, filename)
    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)
    avatar_url = f"{PUBLIC_BASE_URL}{MEDIA_BASE_PATH}/{filename}"
    updated = store.update_user(user.id, avatar_url=avatar_url)
    if updated is None:
        raise HTTPException(status_code=404, detail="user_not_found")
    return ApiResponse(
        ok=True,
        data={
            "user_id": updated.id,
            "name": updated.name,
            "username": updated.username,
            "avatar_url": updated.avatar_url,
            "must_change_password": updated.must_change_password,
        },
    )


@router.post("/invites", response_model=ApiResponse)
def create_invite(req: InviteCreateRequest, user=Depends(get_current_user)):
    invite = store.add_invite(user.id, max_uses=req.max_uses, ttl_sec=req.ttl_sec)
    data = InviteResponse(
        code=invite.code,
        max_uses=invite.max_uses,
        used=invite.used,
        remaining=invite.remaining,
    ).dict()
    return ApiResponse(ok=True, data=data)


@router.get("/invites", response_model=ApiResponse)
def list_invites(user=Depends(get_current_user)):
    invites = store.list_invites(user.id)
    data = [
        InviteResponse(
            code=i.code,
            max_uses=i.max_uses,
            used=i.used,
            remaining=i.remaining,
        ).dict()
        for i in invites
    ]
    return ApiResponse(ok=True, data=data)
