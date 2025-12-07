"""
Authentication API endpoints.
"""

import logging
import secrets
from typing import Any, Optional
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.database import get_db
from app.services.auth_service import auth_service
from app.services.passkey_service import passkey_service
from app.models.user import User
from app.config import settings
from app.main import limiter
from app.schemas import (
    UserCreate,
    UserResponse,
    Token,
    PasskeyRegistrationOptionsRequest,
    PasskeyRegistrationVerifyRequest,
    PasskeyAuthenticationOptionsRequest,
    PasskeyAuthenticationVerifyRequest,
    WebAuthnKeyResponse,
)
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


# --- Passkey (WebAuthn) Endpoints ---

@router.get("/passkey/register/options")
@limiter.limit("5/minute")
async def passkey_register_options(
    request: Request,
    device_name: Optional[str] = None,
    db: Session = Depends(get_db),
) -> Any:
    """
    Generate challenge for passkey registration.
    No authentication required - creates user automatically on verification.
    """
    try:
        # Create a temporary user for passkey registration
        # This user will be used for the passkey
        from app.models.user import User
        
        # Create user with unique identifier
        user_id_str = secrets.token_urlsafe(12)
        temp_email = f"user_{user_id_str}@local"
        
        # Check if user already exists (shouldn't happen, but just in case)
        existing = db.query(User).filter(User.email == temp_email).first()
        if existing:
            temp_user = existing
        else:
            temp_user = User(
                email=temp_email,
                hashed_password="",  # Empty string for passkey-only users
                is_active=True,
            )
            db.add(temp_user)
            db.commit()
            db.refresh(temp_user)
        
        options = passkey_service.generate_registration_options(
            request=request,
            user=temp_user,
            device_name=device_name,
        )
        return options
    except Exception as e:
        logger.error(f"Error generating registration options: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate registration options",
        )


@router.post("/passkey/register/verify", response_model=Token)
@limiter.limit("5/minute")
async def passkey_register_verify(
    request: Request,
    data: PasskeyRegistrationVerifyRequest,
    db: Session = Depends(get_db),
) -> Any:
    """
    Verify registration response and store credential.
    No authentication required - creates user automatically.
    Returns JWT token for immediate login.
    """
    try:
        webauthn_key = passkey_service.verify_registration(
            request=request,
            db=db,
            credential=data.credential,
            challenge=data.challenge,
        )
        
        # Get the user and create token
        user = db.query(User).filter(User.id == webauthn_key.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        
        # Create token for immediate login
        token_data = auth_service.create_user_token(user)
        
        return {
            "success": True,
            "message": "Passkey registered successfully",
            "credential": WebAuthnKeyResponse.model_validate(webauthn_key),
            **token_data,  # Include access_token and token_type
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration verification failed: {str(e)}",
        )


@router.post("/passkey/authenticate/options")
@limiter.limit("5/minute")
async def passkey_authenticate_options(
    request: Request,
    data: PasskeyAuthenticationOptionsRequest,
    db: Session = Depends(get_db),
) -> Any:
    """
    Generate challenge for authentication.
    No authentication required - this is the login endpoint.
    """
    try:
        options = passkey_service.generate_authentication_options(
            request=request,
            db=db,
            username=data.username,
        )
        return options
    except Exception as e:
        logger.error(f"Error generating authentication options: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate authentication options",
        )


@router.post("/passkey/authenticate/verify", response_model=Token)
@limiter.limit("5/minute")
async def passkey_authenticate_verify(
    request: Request,
    data: PasskeyAuthenticationVerifyRequest,
    db: Session = Depends(get_db),
) -> Any:
    """
    Verify authentication response and create session/token.
    No authentication required - this completes the login flow.
    """
    try:
        user = passkey_service.verify_authentication(
            request=request,
            db=db,
            credential=data.credential,
            challenge=data.challenge,
        )
        # Create token using existing auth service
        return auth_service.create_user_token(user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying authentication: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication verification failed: {str(e)}",
        )


@router.get("/passkey/credentials", response_model=list[WebAuthnKeyResponse])
async def list_passkeys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    List all passkeys for the current user.
    """
    credentials = passkey_service.get_user_credentials(db, current_user.id)
    return [WebAuthnKeyResponse.model_validate(cred) for cred in credentials]


@router.delete("/passkey/credentials/{credential_id}")
async def delete_passkey(
    credential_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Delete a passkey credential.
    """
    success = passkey_service.delete_credential(db, credential_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )
    return {"success": True, "message": "Passkey deleted successfully"}
