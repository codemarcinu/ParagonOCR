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
from app.schemas import UserCreate, UserResponse, Token
from app.dependencies import get_current_user

router = APIRouter()


@router.post("/token", response_model=Token)
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


@router.post("/register", response_model=UserResponse)
async def register(user_in: UserCreate, db: Session = Depends(get_db)) -> Any:
    """
    Register a new user.
    """
    user = auth_service.create_user(
        db=db, email=user_in.email, password=user_in.password
    )
    return user


@router.get("/users/me", response_model=UserResponse)
async def read_users_me(
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get current user.
    """
    return current_user
