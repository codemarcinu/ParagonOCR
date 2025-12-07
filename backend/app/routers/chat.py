from typing import List
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.chat_history import Conversation, Message
from app.services.llm_service import chat
from app.services.rag_service import rag_service
from app.schemas import (
    ConversationResponse,
    ConversationCreate,
    MessageResponse,
    MessageCreate,
)

router = APIRouter()


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    """List all conversations."""
    conversations = (
        db.query(Conversation).order_by(Conversation.updated_at.desc()).all()
    )

    # Transform to schema format (needed for last_message property which isn't a direct column)
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


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    request: ConversationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a new conversation."""
    db_conv = Conversation(title=request.title)
    db.add(db_conv)
    db.commit()
    db.refresh(db_conv)

    return db_conv


@router.get(
    "/conversations/{conversation_id}/messages", response_model=List[MessageResponse]
)
async def get_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get messages for a conversation."""
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.timestamp.asc())
        .all()
    )

    return messages


@router.post(
    "/conversations/{conversation_id}/messages", response_model=MessageResponse
)
async def send_message(
    conversation_id: int,
    request: MessageCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
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

    return ai_msg
