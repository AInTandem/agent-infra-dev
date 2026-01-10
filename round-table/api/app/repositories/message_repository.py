# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""Message repository"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import Message as MessageModel
from app.models.message import SendMessageRequest
from app.models.common import generate_id
from app.repositories.base import BaseRepository


class MessageRepository(BaseRepository[MessageModel, SendMessageRequest, dict]):
    """Repository for Message operations (audit log)"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(MessageModel, session)
    
    async def get_by_sandbox(
        self, 
        sandbox_id: str, 
        limit: int = 50
    ) -> list[MessageModel]:
        """Get messages for a sandbox"""
        # Messages where this sandbox is sender or receiver
        result = await self.session.execute(
            select(MessageModel)
            .where(
                (MessageModel.from_sandbox_id == sandbox_id) | 
                (MessageModel.to_sandbox_id == sandbox_id)
            )
            .order_by(MessageModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_by_workspace(
        self, 
        workspace_id: str, 
        limit: int = 50
    ) -> list[MessageModel]:
        """Get messages for a workspace"""
        result = await self.session.execute(
            select(MessageModel)
            .where(MessageModel.workspace_id == workspace_id)
            .order_by(MessageModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def create_message(
        self,
        from_sandbox_id: str,
        to_sandbox_id: str | None,
        workspace_id: str,
        content: dict,
        message_type: str = "request"
    ) -> MessageModel:
        """Create new message (audit log entry)"""
        import json
        
        message_data = {
            "message_id": generate_id("msg"),
            "from_sandbox_id": from_sandbox_id,
            "to_sandbox_id": to_sandbox_id,
            "workspace_id": workspace_id,
            "content_json": json.dumps(content),
            "message_type": message_type,
            "status": "pending",
        }
        
        db_obj = MessageModel(**message_data)
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        
        return db_obj
    
    async def update_status(self, message_id: str, status: str) -> MessageModel | None:
        """Update message status"""
        from sqlalchemy import update
        from app.db.models import Message
        
        stmt = (
            update(Message)
            .where(Message.message_id == message_id)
            .values(status=status)
        )
        await self.session.execute(stmt)
        await self.session.flush()
        
        return await self.get(message_id)
