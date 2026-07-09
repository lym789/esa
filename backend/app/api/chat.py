import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.core.config import get_settings
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.schemas.chat import ConversationCreate, ConversationDetail, ConversationRead, MessageCreate, MessageRead
from app.schemas.trace import TraceRead
from app.services.chat_service import (
    create_conversation,
    get_conversation_for_user,
    list_conversations,
    list_messages,
    send_message,
)
from app.services.trace_service import list_traces_for_conversation
from app.api.traces import trace_to_read


router = APIRouter()
settings = get_settings()


def _message_to_read(message: Message) -> MessageRead:
    return MessageRead(
        id=message.id,
        conversation_id=message.conversation_id,
        role=message.role,
        content=message.content,
        citations=json.loads(message.citations_json),
        metadata=json.loads(message.metadata_json),
        created_at=message.created_at,
    )


def _conversation_detail(db: Session, conversation: Conversation) -> ConversationDetail:
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        user_id=conversation.user_id,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[_message_to_read(message) for message in list_messages(db, conversation)],
    )


def _get_owned_conversation(db: Session, conversation_id: int, current_user: User) -> Conversation:
    conversation = get_conversation_for_user(db, conversation_id, current_user)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return conversation


@router.post("/conversations", response_model=ConversationRead)
def create_chat_conversation(
    payload: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Conversation:
    return create_conversation(db, current_user, title=payload.title)


@router.get("/conversations", response_model=list[ConversationRead])
def list_chat_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Conversation]:
    return list_conversations(db, current_user)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_chat_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationDetail:
    conversation = _get_owned_conversation(db, conversation_id, current_user)
    return _conversation_detail(db, conversation)


@router.post("/conversations/{conversation_id}/messages", response_model=MessageRead)
def send_chat_message(
    conversation_id: int,
    payload: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageRead:
    conversation = _get_owned_conversation(db, conversation_id, current_user)
    assistant_message = send_message(
        db=db,
        conversation=conversation,
        content=payload.content,
        top_k=settings.rag_top_k,
        similarity_threshold=settings.rag_similarity_threshold,
    )
    return _message_to_read(assistant_message)


@router.get("/conversations/{conversation_id}/traces", response_model=list[TraceRead])
def list_chat_conversation_traces(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin"])),
) -> list[TraceRead]:
    return [trace_to_read(trace) for trace in list_traces_for_conversation(db, conversation_id)]
