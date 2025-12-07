"""
API endpoints for AI Chat Assistant.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.llm_service import chat
from app.services.rag_service import rag_service

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    history: list = []


class ChatResponse(BaseModel):
    response: str
    context_used: bool = False


@router.post("/query", response_model=ChatResponse)
async def chat_query(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Process a user query using RAG and LLM.
    """
    # 1. Retrieve context using RAG
    context_text = rag_service.get_context_for_chat(request.message, db)

    # 2. Call LLM
    try:
        # Pass the context and message to the LLM service
        # We construct a context dictionary or string as expected by the service
        # For now, passing text context as a dict for the simple chat function
        context_dict = {"retrieved_info": context_text}

        response_text = chat(query=request.message, context=context_dict)

        return ChatResponse(response=response_text, context_used=bool(context_text))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
