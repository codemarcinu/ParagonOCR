"""
Authentication API endpoints.
"""

from typing import Any
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth_service import auth_service
from app.models.user import User
from app.config import settings
from app.main import limiter

router = APIRouter()


@router.post("/token")
@limiter.limit("5/minute")
async def login_access_token(
    request: Request,
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = auth_service.authenticate_user(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    return auth_service.create_user_token(user)


@router.post("/register")
async def register(email: str, password: str, db: Session = Depends(get_db)) -> Any:
    """
    Register a new user.
    """
    user = auth_service.create_user(db=db, email=email, password=password)
    return {"email": user.email, "id": user.id}


@router.get("/users/me")
async def read_users_me(
    db: Session = Depends(get_db), token: str = Depends(auth_service.oauth2_scheme)
) -> Any:
    """
    Get current user.
    """
    # Ideally use a dependency to get current user from token
    # For now, minimal implementation
    from app.core import security
    from jose import jwt, JWTError

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    user = auth_service.get_user_by_email(db, email=email)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return {"email": user.email, "id": user.id, "is_active": user.is_active}
