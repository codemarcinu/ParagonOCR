"""
ChatHistory database model (Phase 2 - zgodnie z przewodnikiem).
"""

from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime

from app.database import Base


class ChatHistory(Base):
    """Chat history model for Phase 2 (zgodnie z przewodnikiem)."""
    
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True, index=True)
    query = Column(Text, nullable=False)  # User query
    response = Column(Text, nullable=False)  # AI response
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    context = Column(Text, nullable=True)  # RAG context used (JSON string)

