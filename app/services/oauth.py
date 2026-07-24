from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.services.token import create_tokens


def google_auth_url() -> str:
    params = urlencode({
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": f"{settings.APP_URL}/api/v1/auth/oauth/google/callback",
        "response_type": "code",
        "scope": "openid email profile",
    })
    return f"https://accounts.google.com/o/oauth2/auth?{params}"


def github_auth_url() -> str:
    params = urlencode({
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": f"{settings.APP_URL}/api/v1/auth/oauth/github/callback",
        "scope": "user:email",
    })
    return f"https://github.com/login/oauth/authorize?{params}"


async def google_exchange_code(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": f"{settings.APP_URL}/api/v1/auth/oauth/google/callback",
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        tokens = resp.json()
        user_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        user_resp.raise_for_status()
        return user_resp.json()


async def github_exchange_code(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "code": code,
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "redirect_uri": f"{settings.APP_URL}/api/v1/auth/oauth/github/callback",
            },
        )
        resp.raise_for_status()
        tokens = resp.json()
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        user_resp.raise_for_status()
        profile = user_resp.json()
        if not profile.get("email"):
            emails_resp = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
            )
            emails_resp.raise_for_status()
            for e in emails_resp.json():
                if e.get("primary"):
                    profile["email"] = e["email"]
                    break
        return profile


async def oauth_login(db: AsyncSession, provider: str, code: str) -> dict:
    if provider == "google":
        profile = await google_exchange_code(code)
        provider_id = profile["id"]
        email = profile["email"]
        name = profile.get("name", "")
    elif provider == "github":
        profile = await github_exchange_code(code)
        provider_id = str(profile["id"])
        email = profile.get("email", "")
        name = profile.get("name", "")
    else:
        raise ValueError(f"Unknown provider: {provider}")

    id_field = f"{provider}_id"
    result = await db.execute(select(User).where(getattr(User, id_field) == provider_id))
    user = result.scalar_one_or_none()

    if not user and email:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            setattr(user, id_field, provider_id)
            await db.commit()
            await db.refresh(user)

    if not user:
        user = User(
            email=email or f"{provider_id}@{provider}.auth",
            hashed_password=None,
            is_verified=True,
        )
        setattr(user, id_field, provider_id)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    tokens = await create_tokens(db, str(user.id))
    return {"user": user, **tokens}
