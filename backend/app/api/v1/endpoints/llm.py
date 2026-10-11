from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.rbac import get_current_user
from app.db.session import get_db
from app.models.auth import User
from app.schemas.llm import (
    LLMStatusResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatHistoryResponse,
)
from app.services.llm_service import (
    get_llm_status,
    process_chat_message,
    get_chat_history,
    clear_chat_history,
)

router = APIRouter()


@router.get("/status", response_model=LLMStatusResponse)
def check_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Returns live connectivity status, provider configuration, and available tools.
    """
    return get_llm_status(db)


@router.post("/chat", response_model=ChatMessageResponse)
def chat_interaction(
    payload: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Grounded clinical chat endpoint with persona awareness, tool execution & citations.
    """
    if not payload.message.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message text cannot be empty."
        )

    user_name = f"{current_user.first_name or ''} {current_user.last_name or ''}".strip() or None
    role_name = current_user.role.name if current_user.role else "PATIENT"

    return process_chat_message(
        db=db,
        message=payload.message,
        user_id=current_user.id,
        user_role=role_name,
        user_name=user_name,
        session_id=payload.session_id,
        image_path=payload.image_path,
    )


@router.get("/history", response_model=Optional[ChatHistoryResponse])
def fetch_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Returns active consultation conversation history for the signed-in user.
    """
    return get_chat_history(db, current_user.id)


@router.post("/clear")
def clear_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Archives active conversation session to start a fresh chat consultation.
    """
    cleared = clear_chat_history(db, current_user.id)
    return {"status": "success", "session_cleared": cleared}
