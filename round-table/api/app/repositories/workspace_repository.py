# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""Workspace repository"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Workspace as WorkspaceModel
from app.models.workspace import WorkspaceCreateRequest, WorkspaceUpdateRequest
from app.models.common import generate_id
from app.repositories.base import BaseRepository


class WorkspaceRepository(BaseRepository[WorkspaceModel, WorkspaceCreateRequest, WorkspaceUpdateRequest]):
    """Repository for Workspace operations"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(WorkspaceModel, session)
    
    async def get_by_user(self, user_id: str) -> list[WorkspaceModel]:
        """Get all workspaces for a user"""
        return await self.list(user_id=user_id)
    
    async def create_workspace(self, workspace_in: WorkspaceCreateRequest, user_id: str) -> WorkspaceModel:
        """Create new workspace"""
        import json
        from app.models.workspace import WorkspaceSettings
        
        workspace_data = workspace_in.model_dump()
        workspace_data["workspace_id"] = generate_id("ws")
        workspace_data["user_id"] = user_id
        
        # Serialize settings
        if "settings" in workspace_data and workspace_data["settings"]:
            workspace_data["settings_json"] = json.dumps(workspace_data["settings"].model_dump())
            del workspace_data["settings"]
        else:
            workspace_data["settings_json"] = json.dumps(WorkspaceSettings().model_dump())
        
        db_obj = WorkspaceModel(**workspace_data)
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        
        return db_obj
    
    async def update_workspace(
        self, 
        workspace_id: str, 
        workspace_in: WorkspaceUpdateRequest
    ) -> WorkspaceModel | None:
        """Update workspace"""
        import json
        
        # Get existing workspace
        from sqlalchemy import select
        result = await self.session.execute(
            select(WorkspaceModel).where(WorkspaceModel.workspace_id == workspace_id)
        )
        db_obj = result.scalar_one_or_none()
        if not db_obj:
            return None
        
        # Update fields
        update_data = workspace_in.model_dump(exclude_unset=True)
        
        # Handle settings serialization
        if "settings" in update_data and update_data["settings"]:
            update_data["settings_json"] = json.dumps(update_data["settings"].model_dump())
            del update_data["settings"]
        
        for field, value in update_data.items():
            if value is not None and hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        await self.session.flush()
        await self.session.refresh(db_obj)
        
        return db_obj
