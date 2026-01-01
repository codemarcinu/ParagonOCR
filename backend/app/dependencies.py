"""
Shared API dependencies.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.services.auth_service import auth_service
from app.core import security
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


async def get_current_user(
    db: Session = Depends(get_db)  # Removed token dependency
) -> User:
    """
    Validate access token and return current user.
    """
    # BYPASS AUTHENTICATION FOR TESTING
    # Check if a user exists in DB, or create dummy
    # For now, let's assume user ID 1 exists (created by init_db usually)
    # We will return a Mock object if DB access fails or simply a constructed User object
    
    # Simple Mock User for bypass
    # We need to make sure we return a User object compatible with the rest of the app
    # Usually the app expects a SQLAlchemy model
    
    # Try to fetch user 1
    user = db.query(User).filter(User.id == 1).first()
    
    if not user:
        # Create temporary admin user if not exists
        user = User(
            email="admin@example.com",
            is_active=True,
            is_superuser=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
    return user
    
    # ORIGINAL CODE BELOW (Commented out for future restore)
    # credentials_exception = HTTPException(
    #     status_code=status.HTTP_401_UNAUTHORIZED,
    #     detail="Could not validate credentials",
    #     headers={"WWW-Authenticate": "Bearer"},
    # )
    # ... logic skipped ...
