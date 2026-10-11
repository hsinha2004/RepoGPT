from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import aiosqlite
import jwt
from app.auth.security import decode_token
from app.db import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    """Extracts and verifies the authenticated user from the Bearer JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    async with db.execute("SELECT id, email, name, created_at FROM users WHERE email = ?", (email,)) as cursor:
        user = await cursor.fetchone()
        if user is None:
            raise credentials_exception
        return dict(user)
