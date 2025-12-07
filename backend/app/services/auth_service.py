"""
Authentication Service.
"""

from typing import Optional
from datetime import timedelta

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core import security
from app.models.user import User
from app.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


class AuthService:
    def authenticate_user(
        self, db: Session, email: str, password: str
    ) -> Optional[User]:
        """Authenticate a user by email and password."""
        user = self.get_user_by_email(db, email)
        if not user:
            return None
        if not security.verify_password(password, user.hashed_password):
            return None
        return user

    def get_user_by_email(self, db: Session, email: str) -> Optional[User]:
        """Get a user by email."""
        return db.query(User).filter(User.email == email).first()

    def create_user(self, db: Session, email: str, password: str) -> User:
        """Create a new user."""
        existing_user = self.get_user_by_email(db, email)
        if existing_user:
            raise HTTPException(
                status_code=400, detail="User with this email already exists"
            )

        hashed_password = security.get_password_hash(password)
        db_user = User(email=email, hashed_password=hashed_password)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    def create_user_token(self, user: User) -> dict:
        """Create access token for user."""
        access_token_expires = timedelta(minutes=30)  # Default or from settings
        access_token = security.create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}


auth_service = AuthService()
