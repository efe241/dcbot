from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models.user import User
from backend.services.discord_service import DiscordService
from backend.config import settings
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["Auth"])

def get_current_user_id(request: Request) -> str:
    """
    Extracts authenticated discord user id from session cookie or Authorization header.
    """
    token = request.cookies.get("session_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    payload = DiscordService.decode_session_jwt(token)
    if not payload or not payload.get("discord_id"):
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return payload["discord_id"]

@router.get("/login")
async def login(request: Request, state: Optional[str] = None):
    """
    Redirects user to Discord OAuth2 login page.
    """
    referer = request.headers.get("referer") or request.headers.get("origin") or ""
    st = "firebase" if ("web.app" in referer or "firebaseapp.com" in referer or state == "firebase") else "vercel"
    url = DiscordService.get_oauth_login_url(state=st)
    return RedirectResponse(url)

@router.get("/callback")
async def auth_callback(code: str, state: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """
    OAuth2 callback endpoint.
    """
    token_resp = await DiscordService.exchange_code_for_token(code)
    if not token_resp or "access_token" not in token_resp:
        raise HTTPException(status_code=400, detail="Failed to exchange authorization code with Discord")

    access_token = token_resp["access_token"]
    user_profile = await DiscordService.get_user_profile(access_token)
    if not user_profile or "id" not in user_profile:
        raise HTTPException(status_code=400, detail="Failed to fetch user profile from Discord")

    discord_id = str(user_profile["id"])
    username = user_profile.get("username", f"User_{discord_id[:6]}")
    avatar = user_profile.get("avatar")
    email = user_profile.get("email")

    # Upsert user record
    stmt = select(User).where(User.discord_id == discord_id)
    user = (await db.execute(stmt)).scalar_one_or_none()

    if not user:
        user = User(
            discord_id=discord_id,
            discord_username=username,
            discord_avatar=avatar,
            email=email,
            coin_balance=Decimal("0.00")
        )
        db.add(user)
    else:
        user.discord_username = username
        if avatar:
            user.discord_avatar = avatar
        if email:
            user.email = email

    await db.commit()

    # Generate session JWT
    session_jwt = DiscordService.create_session_jwt({
        "id": discord_id,
        "username": username,
        "avatar": avatar,
        "email": email
    })

    target_url = "https://surveytr.web.app/tasks" if state == "firebase" else "/tasks"
    response = RedirectResponse(url=target_url)
    response.set_cookie(
        key="session_token",
        value=session_jwt,
        httponly=True,
        max_age=7 * 24 * 3600,
        samesite="lax"
    )
    return response

@router.post("/mock-login")
async def mock_login(discord_id: str, username: str = "TestUser", db: AsyncSession = Depends(get_db)):
    """
    Mock login endpoint for local testing & preview.
    """
    stmt = select(User).where(User.discord_id == discord_id)
    user = (await db.execute(stmt)).scalar_one_or_none()

    if not user:
        user = User(
            discord_id=discord_id,
            discord_username=username,
            coin_balance=Decimal("1000.00")
        )
        db.add(user)
        await db.commit()

    session_jwt = DiscordService.create_session_jwt({
        "id": discord_id,
        "username": username,
        "avatar": None,
        "email": f"{username.lower()}@example.com"
    })

    response = Response(content='{"status":"ok","message":"Logged in"}', media_type="application/json")
    response.set_cookie(
        key="session_token",
        value=session_jwt,
        httponly=True,
        max_age=7 * 24 * 3600,
        samesite="lax"
    )
    return response

@router.get("/me")
async def get_me(discord_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.discord_id == discord_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    is_admin = discord_id in settings.admin_ids_list or settings.ENVIRONMENT == "development"

    return {
        "discord_id": user.discord_id,
        "discord_username": user.discord_username,
        "discord_avatar": user.discord_avatar,
        "email": user.email,
        "coin_balance": float(user.coin_balance),
        "is_banned": user.is_banned,
        "risk_score": user.risk_score,
        "is_admin": is_admin
    }

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("session_token")
    return {"status": "ok", "message": "Logged out"}
