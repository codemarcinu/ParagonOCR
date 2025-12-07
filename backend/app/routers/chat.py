from typing import List, Optional, Dict
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.chat_history import Conversation, Message
from app.services.llm_service import chat
from app.services.rag_service import rag_service

router = APIRouter()


# Pydantic models
class MessageBase(BaseModel):
    role: str
    content: str
    timestamp: datetime


class ConversationBase(BaseModel):
    id: int
    title: Optional[str]
    last_message: Optional[str] = None
    timestamp: datetime


class CreateConversationRequest(BaseModel):
    title: Optional[str] = None


class SendMessageRequest(BaseModel):
    content: str


@router.get("/conversations", response_model=List[ConversationBase])
async def list_conversations(db: Session = Depends(get_db)):
    """List all conversations."""
    conversations = (
        db.query(Conversation).order_by(Conversation.updated_at.desc()).all()
    )

    result = []
    for conv in conversations:
        last_msg = conv.messages[-1] if conv.messages else None
        result.append(
            {
                "id": conv.id,
                "title": conv.title or "New Conversation",
                "last_message": (
                    last_msg.content[:50] + "..." if last_msg else "No messages"
                ),
                "timestamp": conv.updated_at,
            }
        )
    return result


@router.post("/conversations", response_model=ConversationBase)
async def create_conversation(
    request: CreateConversationRequest = Body(default=CreateConversationRequest()),
    db: Session = Depends(get_db),
):
    """Create a new conversation."""
    db_conv = Conversation(title=request.title)
    db.add(db_conv)
    db.commit()
    db.refresh(db_conv)

    return {
        "id": db_conv.id,
        "title": db_conv.title or "New Conversation",
        "last_message": None,
        "timestamp": db_conv.updated_at,
    }


@router.get(
    "/conversations/{conversation_id}/messages", response_model=List[MessageBase]
)
async def get_messages(conversation_id: int, db: Session = Depends(get_db)):
    """Get messages for a conversation."""
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.timestamp.asc())
        .all()
    )

    return [
        {"role": m.role, "content": m.content, "timestamp": m.timestamp}
        for m in messages
    ]


@router.post("/conversations/{conversation_id}/messages", response_model=MessageBase)
async def send_message(
    conversation_id: int, request: SendMessageRequest, db: Session = Depends(get_db)
):
    """Send a message to a conversation and get AI response."""
    # 1. Verify conversation exists
    conversation = (
        db.query(Conversation).filter(Conversation.id == conversation_id).first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # 2. Save User Message
    user_msg = Message(
        conversation_id=conversation_id, role="user", content=request.content
    )
    db.add(user_msg)

    # 3. Get Context via RAG
    context_text = rag_service.get_context_for_chat(request.content, db)

    # 4. Call LLM
    # Retrieve recent history for context (last 10 messages)
    history = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.timestamp.desc())
        .limit(10)
        .all()
    )
    history.reverse()  # Oldest first

    formatted_history = [{"role": m.role, "content": m.content} for m in history]

    # TODO: Pass history to LLM service properly
    # Assuming chat() takes context dict
    context_dict = {"retrieved_info": context_text}

    try:
        response_text = chat(query=request.content, context=context_dict)
    except Exception as e:
        # Fallback or error
        response_text = "Sorry, I encountered an error processing your request."

    # 5. Save AI Message
    ai_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=response_text,
        context_used=bool(context_text),
    )
    db.add(ai_msg)

    # Update conversation timestamp
    conversation.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(ai_msg)

    return {
        "role": ai_msg.role,
        "content": ai_msg.content,
        "timestamp": ai_msg.timestamp,
    }
