# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""Base repository with common CRUD operations"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Base as SQLBase

ModelType = TypeVar("ModelType", bound=SQLBase)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base repository with common CRUD operations"""
    
    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session
    
    async def get(self, id: str) -> ModelType | None:
        """Get entity by ID"""
        result = await self.session.execute(
            select(self.model).where(self.model.__table__.columns["id"] == id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_field(self, field_name: str, value: Any) -> ModelType | None:
        """Get entity by field value"""
        result = await self.session.execute(
            select(self.model).where(
                self.model.__table__.columns[field_name] == value
            )
        )
        return result.scalar_one_or_none()
    
    async def list(
        self, 
        offset: int = 0, 
        limit: int = 100,
        **filters
    ) -> list[ModelType]:
        """List entities with optional filters"""
        query = select(self.model)
        
        # Apply filters
        for field, value in filters.items():
            if field in self.model.__table__.columns:
                query = query.where(self.model.__table__.columns[field] == value)
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def create(self, obj_in: CreateSchemaType) -> ModelType:
        """Create new entity"""
        # Convert Pydantic model to dict
        obj_data = obj_in.model_dump() if hasattr(obj_in, 'model_dump') else obj_in.dict()
        
        # Create ORM model instance
        db_obj = self.model(**obj_data)
        
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        
        return db_obj
    
    async def update(
        self, 
        id: str, 
        obj_in: UpdateSchemaType | dict[str, Any]
    ) -> ModelType | None:
        """Update entity"""
        # Get existing entity
        db_obj = await self.get(id)
        if not db_obj:
            return None
        
        # Convert to dict if needed
        update_data = (
            obj_in.model_dump(exclude_unset=True) 
            if hasattr(obj_in, 'model_dump')
            else obj_in
        )
        
        # Update fields
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        await self.session.flush()
        await self.session.refresh(db_obj)
        
        return db_obj
    
    async def delete(self, id: str) -> bool:
        """Delete entity"""
        db_obj = await self.get(id)
        if not db_obj:
            return False
        
        await self.session.delete(db_obj)
        await self.session.flush()
        
        return True
    
    async def count(self, **filters) -> int:
        """Count entities with optional filters"""
        from sqlalchemy import func
        
        query = select(func.count()).select_from(self.model)
        
        for field, value in filters.items():
            if field in self.model.__table__.columns:
                query = query.where(self.model.__table__.columns[field] == value)
        
        result = await self.session.execute(query)
        return result.scalar() or 0
