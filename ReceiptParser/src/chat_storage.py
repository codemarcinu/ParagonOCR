"""
Chat Storage for ParagonOCR 2.0

Provides storage and retrieval of AI chat conversations and messages.

Author: ParagonOCR Team
Version: 2.0
"""

from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import json
import logging

from .database import Conversation, ChatMessage, engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

SessionLocal = sessionmaker(bind=engine)


class ChatStorage:
    """
    Chat storage manager for conversations and messages.
    
    Provides methods to create, retrieve, export, and delete
    chat conversations and their messages.
    """
    
    def __init__(self, session: Optional[Session] = None) -> None:
        """
        Initialize chat storage.
        
        Args:
            session: Optional SQLAlchemy session (creates new if None)
        """
        self.session = session if session else SessionLocal()
        self._own_session = session is None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._own_session:
            if exc_type:
                self.session.rollback()
            else:
                self.session.commit()
            self.session.close()
    
    def create_conversation(
        self,
        title: Optional[str] = None,
        model_used: str = "bielik",
        tags: Optional[str] = None
    ) -> int:
        """
        Create a new conversation.
        
        Args:
            title: Conversation title (defaults to 'Nowa rozmowa')
            model_used: Model name used for this conversation
            tags: Optional tags for the conversation
            
        Returns:
            Conversation ID
        """
        try:
            conversation = Conversation(
                title=title or "Nowa rozmowa",
                model_used=model_used,
                tags=tags
            )
            self.session.add(conversation)
            self.session.commit()
            return conversation.conversation_id
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating conversation: {e}")
            raise
    
    def save_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        response_time_ms: Optional[int] = None,
        tokens_used: Optional[int] = None,
        rag_context_used: bool = False
    ) -> int:
        """
        Save a message to a conversation.
        
        Args:
            conversation_id: Conversation ID
            role: Message role ('user' or 'assistant')
            content: Message content
            response_time_ms: Optional response time in milliseconds
            tokens_used: Optional number of tokens used
            rag_context_used: Whether RAG context was used
            
        Returns:
            Message ID
        """
        try:
            if role not in ('user', 'assistant'):
                raise ValueError(f"Invalid role: {role}. Must be 'user' or 'assistant'")
            
            message = ChatMessage(
                conversation_id=conversation_id,
                role=role,
                content=content,
                response_time_ms=response_time_ms,
                tokens_used=tokens_used,
                rag_context_used=rag_context_used
            )
            self.session.add(message)
            self.session.commit()
            return message.message_id
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error saving message: {e}")
            raise
    
    def get_conversation_history(self, conversation_id: int) -> List[Dict]:
        """
        Get conversation history (all messages).
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            List of message dictionaries
        """
        try:
            messages = (
                self.session.query(ChatMessage)
                .filter_by(conversation_id=conversation_id)
                .order_by(ChatMessage.timestamp)
                .all()
            )
            
            return [
                {
                    "message_id": msg.message_id,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                    "response_time_ms": msg.response_time_ms,
                    "tokens_used": msg.tokens_used,
                    "rag_context_used": msg.rag_context_used
                }
                for msg in messages
            ]
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []
    
    def list_conversations(self, limit: int = 50) -> List[Dict]:
        """
        List conversations.
        
        Args:
            limit: Maximum number of conversations to return
            
        Returns:
            List of conversation dictionaries
        """
        try:
            conversations = (
                self.session.query(Conversation)
                .order_by(Conversation.created_at.desc())
                .limit(limit)
                .all()
            )
            
            return [
                {
                    "conversation_id": conv.conversation_id,
                    "created_at": conv.created_at.isoformat() if conv.created_at else None,
                    "title": conv.title,
                    "model_used": conv.model_used,
                    "tags": conv.tags,
                    "message_count": len(conv.messages)
                }
                for conv in conversations
            ]
        except Exception as e:
            logger.error(f"Error listing conversations: {e}")
            return []
    
    def export_conversation(
        self,
        conversation_id: int,
        format: str = "txt"
    ) -> str:
        """
        Export conversation to text or JSON format.
        
        Args:
            conversation_id: Conversation ID
            format: Export format ('txt' or 'json')
            
        Returns:
            Exported conversation as string
        """
        try:
            conversation = (
                self.session.query(Conversation)
                .filter_by(conversation_id=conversation_id)
                .first()
            )
            
            if not conversation:
                raise ValueError(f"Conversation {conversation_id} not found")
            
            messages = self.get_conversation_history(conversation_id)
            
            if format == "json":
                export_data = {
                    "conversation_id": conversation.conversation_id,
                    "title": conversation.title,
                    "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
                    "model_used": conversation.model_used,
                    "tags": conversation.tags,
                    "messages": messages
                }
                return json.dumps(export_data, indent=2, ensure_ascii=False)
            
            elif format == "txt":
                lines = [
                    f"Konwersacja: {conversation.title}",
                    f"Utworzona: {conversation.created_at}",
                    f"Model: {conversation.model_used}",
                    f"ID: {conversation_id}",
                    "",
                    "=" * 60,
                    ""
                ]
                
                for msg in messages:
                    role_str = "Użytkownik" if msg["role"] == "user" else "AI"
                    timestamp = msg["timestamp"]
                    if timestamp:
                        try:
                            dt = datetime.fromisoformat(timestamp)
                            time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                        except:
                            time_str = timestamp
                    else:
                        time_str = "N/A"
                    
                    lines.append(f"[{time_str}] {role_str}:")
                    lines.append(msg["content"])
                    lines.append("")
                
                return "\n".join(lines)
            
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            logger.error(f"Error exporting conversation: {e}")
            raise
    
    def delete_conversation(self, conversation_id: int) -> bool:
        """
        Delete a conversation and all its messages.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            True if deleted, False if not found
        """
        try:
            conversation = (
                self.session.query(Conversation)
                .filter_by(conversation_id=conversation_id)
                .first()
            )
            
            if not conversation:
                return False
            
            self.session.delete(conversation)
            self.session.commit()
            return True
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error deleting conversation: {e}")
            return False
    
    def get_conversation(self, conversation_id: int) -> Optional[Dict]:
        """
        Get conversation details.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Conversation dictionary or None if not found
        """
        try:
            conversation = (
                self.session.query(Conversation)
                .filter_by(conversation_id=conversation_id)
                .first()
            )
            
            if not conversation:
                return None
            
            return {
                "conversation_id": conversation.conversation_id,
                "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
                "title": conversation.title,
                "model_used": conversation.model_used,
                "tags": conversation.tags
            }
        except Exception as e:
            logger.error(f"Error getting conversation: {e}")
            return None
    
    def update_conversation_title(
        self,
        conversation_id: int,
        title: str
    ) -> bool:
        """
        Update conversation title.
        
        Args:
            conversation_id: Conversation ID
            title: New title
            
        Returns:
            True if updated, False if not found
        """
        try:
            conversation = (
                self.session.query(Conversation)
                .filter_by(conversation_id=conversation_id)
                .first()
            )
            
            if not conversation:
                return False
            
            conversation.title = title
            self.session.commit()
            return True
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating conversation title: {e}")
            return False

