import httpx
import jwt
import datetime
from typing import Dict, Any, Optional
from backend.config import settings
import logging

logger = logging.getLogger(__name__)

DISCORD_API_BASE = "https://discord.com/api/v10"

import urllib.request
import urllib.parse
import json

class DiscordService:
    @staticmethod
    async def exchange_code_for_token(code: str) -> Optional[Dict[str, Any]]:
        """
        Exchanges Discord OAuth2 authorization code for an access token.
        """
        data = {
            "client_id": settings.DISCORD_CLIENT_ID,
            "client_secret": settings.DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.DISCORD_REDIRECT_URI
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "SurveyTR/1.0"
        }

        # Try httpx first
        try:
            async with httpx.AsyncClient(trust_env=True, timeout=15.0) as client:
                res = await client.post(f"{DISCORD_API_BASE}/oauth2/token", data=data, headers=headers)
                if res.status_code == 200:
                    return res.json()
                logger.error(f"Discord Token Exchange failed ({res.status_code}): {res.text}")
        except Exception as e:
            logger.warning(f"httpx exchange_code_for_token failed ({e}). Trying urllib fallback...")

        # Fallback to standard urllib for Vercel Serverless compatibility
        try:
            encoded_data = urllib.parse.urlencode(data).encode("utf-8")
            req = urllib.request.Request(
                f"{DISCORD_API_BASE}/oauth2/token",
                data=encoded_data,
                headers=headers
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.error(f"urllib exchange_code_for_token exception: {e}")

        return None

    @staticmethod
    async def get_user_profile(access_token: str) -> Optional[Dict[str, Any]]:
        """
        Fetches Discord user profile using access token.
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "SurveyTR/1.0"
        }

        # Try httpx first
        try:
            async with httpx.AsyncClient(trust_env=True, timeout=15.0) as client:
                res = await client.get(f"{DISCORD_API_BASE}/users/@me", headers=headers)
                if res.status_code == 200:
                    return res.json()
                logger.error(f"Discord User Profile fetch failed ({res.status_code}): {res.text}")
        except Exception as e:
            logger.warning(f"httpx get_user_profile failed ({e}). Trying urllib fallback...")

        # Fallback to standard urllib
        try:
            req = urllib.request.Request(f"{DISCORD_API_BASE}/users/@me", headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.error(f"urllib get_user_profile exception: {e}")

        return None

    @staticmethod
    def create_session_jwt(user_data: Dict[str, Any]) -> str:
        payload = {
            "discord_id": user_data.get("id"),
            "username": user_data.get("username"),
            "avatar": user_data.get("avatar"),
            "email": user_data.get("email"),
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

    @staticmethod
    def decode_session_jwt(token: str) -> Optional[Dict[str, Any]]:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            return payload
        except Exception:
            return None

    @staticmethod
    def get_oauth_login_url(state: str = "default") -> str:
        return (
            f"{DISCORD_API_BASE}/oauth2/authorize"
            f"?client_id={settings.DISCORD_CLIENT_ID}"
            f"&redirect_uri={httpx.URL(settings.DISCORD_REDIRECT_URI)}"
            f"&response_type=code"
            f"&scope=identify%20email"
            f"&state={state}"
        )
