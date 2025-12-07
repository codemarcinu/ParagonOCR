"""
WebAuthn Key database model for passkey authentication.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class WebAuthnKey(Base):
    """WebAuthn credential (passkey) model for FIDO2 authentication."""

    __tablename__ = "webauthn_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    credential_id = Column(String, unique=True, nullable=False, index=True)  # Base64 encoded
    public_key = Column(String, nullable=False)  # Base64 encoded public key
    device_name = Column(String, nullable=True)  # User-friendly name (e.g., "iPhone 15")
    device_type = Column(String, default="single-device")  # single-device or cross-device
    last_used = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    transports = Column(JSON, nullable=True)  # Array of transport strings: ["internal", "usb", "ble", "nfc", "hybrid"]

    # Relationship
    user = relationship("User", backref="webauthn_keys")

    __table_args__ = (
        Index("idx_webauthn_user_credential", "user_id", "credential_id"),
    )

    def __repr__(self):
        return f"<WebAuthnKey(id={self.id}, user_id={self.user_id}, device_name={self.device_name})>"

