from fastapi import APIRouter, Depends, HTTPException, status
import aiosqlite
from app.auth.security import hash_password, verify_password, create_access_token
from app.db import get_db
from app.models import UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: aiosqlite.Connection = Depends(get_db)):
    """Registers a new user account."""
    async with db.execute("SELECT id FROM users WHERE email = ?", (user_in.email,)) as cursor:
        existing = await cursor.fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

    pwd_hash = hash_password(user_in.password)
    async with db.execute(
        "INSERT INTO users (email, name, password_hash) VALUES (?, ?, ?)",
        (user_in.email, user_in.name, pwd_hash),
    ) as cursor:
        user_id = cursor.lastrowid
        await db.commit()

    async with db.execute("SELECT id, email, name, created_at FROM users WHERE id = ?", (user_id,)) as cursor:
        user = await cursor.fetchone()
        return dict(user)


@router.post("/login")
async def login(credentials: dict, db: aiosqlite.Connection = Depends(get_db)):
    """Authenticates a user and returns an access token."""
    email = credentials.get("email")
    password = credentials.get("password")
    if not email or not password:
        raise HTTPException(status_code=400, detail="Missing email or password")

    async with db.execute("SELECT id, email, password_hash FROM users WHERE email = ?", (email,)) as cursor:
        user = await cursor.fetchone()
        if not user or not verify_password(password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": user["email"], "uid": user["id"]})
    return {"access_token": token, "token_type": "bearer"}
