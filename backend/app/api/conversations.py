import logging
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, or_

from app.api.deps import get_current_active_user
from app.core.db import get_db
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    MessageCreate,
    MessageResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("", response_model=List[ConversationResponse])
async def list_conversations(
    module: Optional[str] = Query(None, description="Filter conversations by module (e.g. chat, interview)"),
    q: Optional[str] = Query(None, description="Search query string to filter conversations"),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List all persistent conversations for the authenticated user, ordered by pinned & updated timestamp."""
    query = select(Conversation).filter(Conversation.user_id == current_user.id)
    
    if module:
        query = query.filter(Conversation.module == module)
        
    if q and q.strip():
        search_term = f"%{q.strip()}%"
        # Subquery for matching message contents
        matching_msg_convs = (
            select(Message.conversation_id)
            .filter(Message.content.ilike(search_term))
            .scalar_subquery()
        )
        query = query.filter(
            or_(
                Conversation.title.ilike(search_term),
                Conversation.id.in_(matching_msg_convs)
            )
        )

    # Order pinned first, then newest updated
    query = query.order_by(
        Conversation.is_pinned.desc().nullslast(),
        Conversation.updated_at.desc()
    ).limit(limit)

    result = await db.execute(query)
    conversations = result.scalars().all()

    response = []
    for conv in conversations:
        msg_count_res = await db.execute(
            select(func.count(Message.id)).filter(Message.conversation_id == conv.id)
        )
        msg_count = msg_count_res.scalar() or 0

        response.append(ConversationResponse(
            id=conv.id,
            user_id=conv.user_id,
            module=conv.module,
            title=conv.title,
            summary=conv.summary,
            is_pinned=getattr(conv, "is_pinned", False) or False,
            is_archived=getattr(conv, "is_archived", False) or False,
            current_state=conv.current_state,
            metadata=conv.metadata_,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=msg_count,
            messages=None
        ))
    return response


@router.get("/recent", response_model=List[ConversationResponse])
async def list_recent_conversations(
    module: Optional[str] = Query("chat", description="Module filter"),
    limit: int = Query(10, ge=1, le=20),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve top recent conversations for the authenticated user."""
    return await list_conversations(module=module, q=None, limit=limit, current_user=current_user, db=db)


@router.get("/search", response_model=List[ConversationResponse])
async def search_conversations(
    q: str = Query(..., min_length=1, description="Search query string"),
    module: Optional[str] = Query(None, description="Module filter"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Search conversations by title or message content."""
    return await list_conversations(module=module, q=q, limit=30, current_user=current_user, db=db)


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conv_in: ConversationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new persistent conversation for the authenticated user."""
    conv_id = str(uuid.uuid4())
    conv = Conversation(
        id=conv_id,
        user_id=current_user.id,
        module=conv_in.module,
        title=conv_in.title or "New Conversation",
        is_pinned=conv_in.is_pinned or False,
        is_archived=conv_in.is_archived or False,
        current_state=conv_in.current_state or {},
        metadata_=conv_in.metadata_ or {}
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)

    return ConversationResponse(
        id=conv.id,
        user_id=conv.user_id,
        module=conv.module,
        title=conv.title,
        summary=conv.summary,
        is_pinned=conv.is_pinned or False,
        is_archived=conv.is_archived or False,
        current_state=conv.current_state,
        metadata=conv.metadata_,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=0,
        messages=[]
    )


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a conversation by ID with all its messages in chronological order."""
    query = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
    )
    result = await db.execute(query)
    conv = result.scalars().first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages_res = [
        MessageResponse(
            id=m.id,
            conversation_id=m.conversation_id,
            role=m.role,
            content=m.content,
            sources=m.sources,
            metadata=m.metadata_,
            created_at=m.created_at
        )
        for m in (conv.messages or [])
    ]

    return ConversationResponse(
        id=conv.id,
        user_id=conv.user_id,
        module=conv.module,
        title=conv.title,
        summary=conv.summary,
        is_pinned=getattr(conv, "is_pinned", False) or False,
        is_archived=getattr(conv, "is_archived", False) or False,
        current_state=conv.current_state,
        metadata=conv.metadata_,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=len(messages_res),
        messages=messages_res
    )


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get messages for a specific conversation."""
    conv_res = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    if not conv_res.scalars().first():
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages_res = await db.execute(
        select(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return [
        MessageResponse(
            id=m.id,
            conversation_id=m.conversation_id,
            role=m.role,
            content=m.content,
            sources=m.sources,
            metadata=m.metadata_,
            created_at=m.created_at
        )
        for m in messages_res.scalars().all()
    ]


@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def add_message(
    conversation_id: str,
    msg_in: MessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Append a message to a conversation. Scoped strictly to the authenticated user."""
    result = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    conv = result.scalars().first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msg_id = str(uuid.uuid4())
    msg = Message(
        id=msg_id,
        conversation_id=conversation_id,
        role=msg_in.role,
        content=msg_in.content,
        sources=msg_in.sources,
        metadata_=msg_in.metadata_
    )
    db.add(msg)

    # Automatically set title from first user message if still default
    if conv.title in ["New Conversation", "New Discussion"] and msg_in.role == "user":
        first_line = msg_in.content.strip().split("\n")[0][:45]
        if first_line:
            conv.title = first_line

    await db.commit()
    await db.refresh(msg)

    return MessageResponse(
        id=msg.id,
        conversation_id=msg.conversation_id,
        role=msg.role,
        content=msg.content,
        sources=msg.sources,
        metadata=msg.metadata_,
        created_at=msg.created_at
    )


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    conv_update: ConversationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update title, pinned state, archived state, summary, or module state snapshot."""
    result = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    conv = result.scalars().first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conv_update.title is not None:
        conv.title = conv_update.title
    if conv_update.is_pinned is not None:
        conv.is_pinned = conv_update.is_pinned
    if conv_update.is_archived is not None:
        conv.is_archived = conv_update.is_archived
    if conv_update.summary is not None:
        conv.summary = conv_update.summary
    if conv_update.current_state is not None:
        conv.current_state = conv_update.current_state
    if conv_update.metadata_ is not None:
        conv.metadata_ = conv_update.metadata_

    await db.commit()
    await db.refresh(conv)

    msg_count_res = await db.execute(
        select(func.count(Message.id)).filter(Message.conversation_id == conv.id)
    )
    msg_count = msg_count_res.scalar() or 0

    return ConversationResponse(
        id=conv.id,
        user_id=conv.user_id,
        module=conv.module,
        title=conv.title,
        summary=conv.summary,
        is_pinned=getattr(conv, "is_pinned", False) or False,
        is_archived=getattr(conv, "is_archived", False) or False,
        current_state=conv.current_state,
        metadata=conv.metadata_,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=msg_count,
        messages=None
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a conversation and all its messages."""
    result = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    conv = result.scalars().first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await db.delete(conv)
    await db.commit()
    return None
