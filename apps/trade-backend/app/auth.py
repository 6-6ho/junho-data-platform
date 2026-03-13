import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel

SETTINGS_PASSWORD = os.getenv("SETTINGS_PASSWORD", "admin")
SETTINGS_JWT_SECRET = os.getenv("SETTINGS_JWT_SECRET", "dev-jwt-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

security = HTTPBearer()

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def create_access_token() -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    return jwt.encode({"exp": expire, "sub": "settings"}, SETTINGS_JWT_SECRET, algorithm=ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    try:
        payload = jwt.decode(credentials.credentials, SETTINGS_JWT_SECRET, algorithms=[ALGORITHM])
        if payload.get("sub") != "settings":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


@auth_router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    if req.password != SETTINGS_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong password")
    return TokenResponse(access_token=create_access_token())


@auth_router.get("/verify")
def verify(user: str = Depends(get_current_user)):
    return {"authenticated": True}
