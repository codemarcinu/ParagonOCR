"""
Passkey (WebAuthn) authentication service.

Handles challenge generation, credential registration, and authentication verification.
"""

import base64
import secrets
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from urllib.parse import urlparse

from sqlalchemy.orm import Session
from fastapi import HTTPException, status, Request

try:
    # Try py_webauthn first (more common)
    from webauthn import (
        generate_registration_options,
        verify_registration_response,
        generate_authentication_options,
        verify_authentication_response,
        options_to_json,
    )
    from webauthn.helpers.structs import (
        PublicKeyCredentialDescriptor,
        AuthenticatorSelectionCriteria,
        AuthenticatorAttachment,
        UserVerificationRequirement,
        RegistrationCredential,
        AuthenticationCredential,
        AuthenticatorAttestationResponse,
        AuthenticatorAssertionResponse,
        AuthenticatorTransport,
    )
    from webauthn.helpers import bytes_to_base64url, base64url_to_bytes
except ImportError:
    # Fallback: We'll implement a basic version or raise an error
    logger.error("webauthn library not found. Please install: pip install py-webauthn")
    raise ImportError("webauthn library is required. Install with: pip install py-webauthn")

from app.models.user import User
from app.models.webauthn_key import WebAuthnKey
from app.config import settings

logger = logging.getLogger(__name__)

# Challenge storage (in production, use Redis or database)
_challenge_store: Dict[str, Dict[str, Any]] = {}
CHALLENGE_EXPIRY_MINUTES = 10


def _get_origin(request: Request) -> str:
    """Extract origin from request."""
    origin = request.headers.get("origin")
    if not origin:
        # Fallback to host header
        host = request.headers.get("host", "localhost:8000")
        scheme = "https" if request.url.scheme == "https" else "http"
        origin = f"{scheme}://{host}"
    
    # For localhost development, normalize origin
    # Frontend on :5173 and backend on :8000 should both use localhost as RP ID
    parsed = urlparse(origin)
    if parsed.hostname in ["localhost", "127.0.0.1"]:
        # Keep the original origin for validation, but RP ID will be just "localhost"
        pass
    
    return origin


def _get_rp_id(origin: str) -> str:
    """Extract RP ID from origin.
    
    For localhost, always use "localhost" as RP ID regardless of port.
    This allows frontend (localhost:5173) and backend (localhost:8000) to work together.
    """
    parsed = urlparse(origin)
    hostname = parsed.hostname or "localhost"
    
    # For localhost/127.0.0.1, always use "localhost" as RP ID
    # This is required for WebAuthn to work across different ports on localhost
    if hostname in ["localhost", "127.0.0.1"]:
        return "localhost"
    
    return hostname


def _store_challenge(challenge: str, data: Dict[str, Any], expiry_minutes: int = CHALLENGE_EXPIRY_MINUTES):
    """Store challenge with expiration."""
    expiry = datetime.utcnow() + timedelta(minutes=expiry_minutes)
    _challenge_store[challenge] = {
        **data,
        "expires_at": expiry,
    }
    logger.debug(f"Stored challenge: {challenge[:20]}... (expires at {expiry})")


def _get_challenge(challenge: str) -> Optional[Dict[str, Any]]:
    """Get challenge data if valid and not expired."""
    stored = _challenge_store.get(challenge)
    if not stored:
        return None
    
    if datetime.utcnow() > stored["expires_at"]:
        logger.debug(f"Challenge expired: {challenge[:20]}...")
        _challenge_store.pop(challenge, None)
        return None
    
    return stored


def _cleanup_expired_challenges():
    """Remove expired challenges from store."""
    now = datetime.utcnow()
    expired = [
        key for key, value in _challenge_store.items()
        if now > value.get("expires_at", datetime.utcnow())
    ]
    for key in expired:
        _challenge_store.pop(key, None)


class PasskeyService:
    """Service for WebAuthn passkey operations."""

    def generate_registration_options(
        self, request: Request, user: User, device_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate registration options for passkey creation.
        
        Args:
            request: FastAPI request object
            user: User model instance
            device_name: Optional device name for the credential
            
        Returns:
            PublicKeyCredentialCreationOptions as dict
        """
        origin = _get_origin(request)
        rp_id = _get_rp_id(origin)
        
        # Generate challenge
        challenge = secrets.token_urlsafe(32)
        
        # Generate registration options
        # Use user ID as username for passkey-only auth
        user_name = user.email or f"user_{user.id}"
        user_display_name = user.email or f"User {user.id}"
        
        options = generate_registration_options(
            rp_id=rp_id,
            rp_name="ParagonOCR",
            user_id=base64url_to_bytes(str(user.id).encode()),
            user_name=user_name,
            user_display_name=user_display_name,
            challenge=base64url_to_bytes(challenge),
            authenticator_selection=AuthenticatorSelectionCriteria(
                authenticator_attachment=None,  # Allow both platform and cross-platform
                user_verification=UserVerificationRequirement.DISCOURAGED,  # Most compatible
                require_resident_key=False,  # Don't require resident key
            ),
            timeout=300000,  # 5 minutes timeout (more generous)
        )
        
        # Store challenge with user info
        _store_challenge(
            challenge,
            {
                "type": "registration",
                "user_id": user.id,
                "user_email": user.email,
                "device_name": device_name,
                "origin": origin,
                "rp_id": rp_id,
            }
        )
        
        # Convert to JSON-serializable dict
        # options_to_json returns a JSON string, parse it to dict
        options_json = options_to_json(options)
        options_dict = json.loads(options_json) if isinstance(options_json, str) else options_json
        options_dict["challenge"] = challenge  # Replace bytes with string
        
        # Ensure rpId is set (SimpleWebAuthn expects rpId, not rp.id)
        if "rp" in options_dict and "id" in options_dict["rp"]:
            options_dict["rpId"] = options_dict["rp"]["id"]
        
        user_name = user.email or f"user_{user.id}"
        logger.info(f"Generated registration options for user {user_name}, rp_id={rp_id}, origin={origin}")
        return options_dict

    def verify_registration(
        self,
        request: Request,
        db: Session,
        credential: Dict[str, Any],
        challenge: str,
    ) -> WebAuthnKey:
        """
        Verify registration response and store credential.
        
        Args:
            request: FastAPI request object
            db: Database session
            credential: Registration credential from client
            challenge: Challenge string from registration options
            
        Returns:
            Created WebAuthnKey instance
        """
        # Get and validate challenge
        challenge_data = _get_challenge(challenge)
        if not challenge_data or challenge_data.get("type") != "registration":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired challenge",
            )
        
        user_id = challenge_data["user_id"]
        origin = challenge_data["origin"]
        rp_id = challenge_data["rp_id"]
        
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        
        # Verify registration
        try:
            # Parse credential from dict (frontend sends JSON)
            # credential structure: { id, rawId, response: { clientDataJSON, attestationObject, transports }, type }
            cred_id = credential.get("id") or credential.get("credentialId")
            raw_id = credential.get("rawId")
            if isinstance(raw_id, str):
                raw_id_bytes = base64url_to_bytes(raw_id)
            else:
                raw_id_bytes = raw_id
            
            response_data = credential.get("response", {})
            client_data_json = response_data.get("clientDataJSON")
            attestation_object = response_data.get("attestationObject")
            
            # Convert to bytes if strings
            if isinstance(client_data_json, str):
                client_data_json_bytes = base64url_to_bytes(client_data_json)
            else:
                client_data_json_bytes = client_data_json
            
            if isinstance(attestation_object, str):
                attestation_object_bytes = base64url_to_bytes(attestation_object)
            else:
                attestation_object_bytes = attestation_object
            
            # Parse transports
            transports_list = response_data.get("transports", [])
            if transports_list:
                transports = [AuthenticatorTransport(t) for t in transports_list if t]
            else:
                transports = None
            
            # Create response object
            attestation_response = AuthenticatorAttestationResponse(
                client_data_json=client_data_json_bytes,
                attestation_object=attestation_object_bytes,
                transports=transports,
            )
            
            # Create credential object
            cred_obj = RegistrationCredential(
                id=cred_id,
                raw_id=raw_id_bytes,
                response=attestation_response,
                authenticator_attachment=None,  # Optional
            )
            
            registration_verification = verify_registration_response(
                credential=cred_obj,
                expected_challenge=base64url_to_bytes(challenge),
                expected_rp_id=rp_id,
                expected_origin=origin,
            )
        except Exception as e:
            logger.error(f"Registration verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Registration verification failed: {str(e)}",
            )
        
        # Check if credential already exists
        credential_id_b64 = bytes_to_base64url(registration_verification.credential_id)
        existing = db.query(WebAuthnKey).filter(
            WebAuthnKey.credential_id == credential_id_b64
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credential already registered",
            )
        
        # Store credential
        public_key_b64 = base64.b64encode(
            registration_verification.credential_public_key
        ).decode("utf-8")
        
        webauthn_key = WebAuthnKey(
            user_id=user.id,
            credential_id=credential_id_b64,
            public_key=public_key_b64,
            device_name=challenge_data.get("device_name"),
            device_type="single-device",
            transports=credential.get("transports", []),
            created_at=datetime.utcnow(),
        )
        
        db.add(webauthn_key)
        db.commit()
        db.refresh(webauthn_key)
        
        # Clean up challenge
        _challenge_store.pop(challenge, None)
        
        logger.info(f"Registered passkey for user {user.email} (device: {webauthn_key.device_name})")
        return webauthn_key

    def generate_authentication_options(
        self, request: Request, db: Session, username: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate authentication options for passkey login.
        
        Args:
            request: FastAPI request object
            db: Database session
            username: Optional username/email to filter credentials
            
        Returns:
            PublicKeyCredentialRequestOptions as dict
        """
        origin = _get_origin(request)
        rp_id = _get_rp_id(origin)
        
        # Generate challenge
        challenge = secrets.token_urlsafe(32)
        
        # Get user's credentials
        allow_credentials = []
        if username:
            user = db.query(User).filter(User.email == username).first()
            if user:
                credentials = db.query(WebAuthnKey).filter(
                    WebAuthnKey.user_id == user.id
                ).all()
                for cred in credentials:
                    allow_credentials.append(
                        PublicKeyCredentialDescriptor(
                            id=base64url_to_bytes(cred.credential_id),
                            transports=cred.transports or [],
                        )
                    )
        
        # Generate authentication options
        options = generate_authentication_options(
            rp_id=rp_id,
            challenge=base64url_to_bytes(challenge),
            allow_credentials=allow_credentials if allow_credentials else None,
            user_verification=UserVerificationRequirement.DISCOURAGED,  # Most compatible
            timeout=300000,  # 5 minutes timeout (more generous)
        )
        
        # Store challenge
        _store_challenge(
            challenge,
            {
                "type": "authentication",
                "username": username,
                "origin": origin,
                "rp_id": rp_id,
            }
        )
        
        # Convert to JSON-serializable dict
        # options_to_json returns a JSON string, parse it to dict
        options_json = options_to_json(options)
        options_dict = json.loads(options_json) if isinstance(options_json, str) else options_json
        options_dict["challenge"] = challenge  # Replace bytes with string
        
        # Ensure rpId is set (SimpleWebAuthn expects rpId)
        if "rpId" not in options_dict:
            options_dict["rpId"] = rp_id
        
        logger.info(f"Generated authentication options for {username or 'any user'}, rp_id={rp_id}, origin={origin}")
        return options_dict

    def verify_authentication(
        self,
        request: Request,
        db: Session,
        credential: Dict[str, Any],
        challenge: str,
    ) -> User:
        """
        Verify authentication response and return authenticated user.
        
        Args:
            request: FastAPI request object
            db: Database session
            credential: Authentication credential from client
            challenge: Challenge string from authentication options
            
        Returns:
            Authenticated User instance
        """
        # Get and validate challenge
        challenge_data = _get_challenge(challenge)
        if not challenge_data or challenge_data.get("type") != "authentication":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired challenge",
            )
        
        origin = challenge_data["origin"]
        rp_id = challenge_data["rp_id"]
        
        # Get credential from database
        credential_id = credential.get("id")
        if not credential_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing credential ID",
            )
        
        # Decode credential ID
        try:
            credential_id_bytes = base64url_to_bytes(credential_id)
            credential_id_b64 = bytes_to_base64url(credential_id_bytes)
        except Exception as e:
            logger.error(f"Invalid credential ID format: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid credential ID format",
            )
        
        webauthn_key = db.query(WebAuthnKey).filter(
            WebAuthnKey.credential_id == credential_id_b64
        ).first()
        
        if not webauthn_key:
            logger.warning(f"Authentication attempt with unknown credential: {credential_id[:20]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credential",
            )
        
        # Get user
        user = db.query(User).filter(User.id == webauthn_key.user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )
        
        # Verify authentication
        try:
            public_key_bytes = base64.b64decode(webauthn_key.public_key)
            
            # Parse credential from dict (frontend sends JSON)
            # credential structure: { id, rawId, response: { clientDataJSON, authenticatorData, signature, userHandle }, type }
            cred_id = credential.get("id") or credential.get("credentialId")
            raw_id = credential.get("rawId")
            if isinstance(raw_id, str):
                raw_id_bytes = base64url_to_bytes(raw_id)
            else:
                raw_id_bytes = raw_id
            
            response_data = credential.get("response", {})
            client_data_json = response_data.get("clientDataJSON")
            authenticator_data = response_data.get("authenticatorData")
            signature = response_data.get("signature")
            user_handle = response_data.get("userHandle")
            
            # Convert to bytes if strings
            if isinstance(client_data_json, str):
                client_data_json_bytes = base64url_to_bytes(client_data_json)
            else:
                client_data_json_bytes = client_data_json
            
            if isinstance(authenticator_data, str):
                authenticator_data_bytes = base64url_to_bytes(authenticator_data)
            else:
                authenticator_data_bytes = authenticator_data
            
            if isinstance(signature, str):
                signature_bytes = base64url_to_bytes(signature)
            else:
                signature_bytes = signature
            
            user_handle_bytes = None
            if user_handle:
                if isinstance(user_handle, str):
                    user_handle_bytes = base64url_to_bytes(user_handle)
                else:
                    user_handle_bytes = user_handle
            
            # Create response object
            assertion_response = AuthenticatorAssertionResponse(
                client_data_json=client_data_json_bytes,
                authenticator_data=authenticator_data_bytes,
                signature=signature_bytes,
                user_handle=user_handle_bytes,
            )
            
            # Create credential object
            cred_obj = AuthenticationCredential(
                id=cred_id,
                raw_id=raw_id_bytes,
                response=assertion_response,
                authenticator_attachment=None,  # Optional
            )
            
            authentication_verification = verify_authentication_response(
                credential=cred_obj,
                expected_challenge=base64url_to_bytes(challenge),
                expected_rp_id=rp_id,
                expected_origin=origin,
                credential_public_key=public_key_bytes,
                credential_current_sign_count=0,  # TODO: Track sign count for replay protection
            )
        except Exception as e:
            logger.error(f"Authentication verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication verification failed: {str(e)}",
            )
        
        # Update last used timestamp
        webauthn_key.last_used = datetime.utcnow()
        db.commit()
        
        # Clean up challenge
        _challenge_store.pop(challenge, None)
        
        logger.info(f"Successful passkey authentication for user {user.email}")
        return user

    def get_user_credentials(self, db: Session, user_id: int) -> List[WebAuthnKey]:
        """Get all passkeys for a user."""
        return db.query(WebAuthnKey).filter(
            WebAuthnKey.user_id == user_id
        ).order_by(WebAuthnKey.created_at.desc()).all()

    def delete_credential(self, db: Session, credential_id: int, user_id: int) -> bool:
        """Delete a passkey credential."""
        credential = db.query(WebAuthnKey).filter(
            WebAuthnKey.id == credential_id,
            WebAuthnKey.user_id == user_id,
        ).first()
        
        if not credential:
            return False
        
        db.delete(credential)
        db.commit()
        logger.info(f"Deleted passkey {credential_id} for user {user_id}")
        return True


# Global service instance
passkey_service = PasskeyService()

