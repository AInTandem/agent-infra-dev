"""Sandbox repository"""

from sqlalchemy.ext.asyncio import AsyncSession

from api.app.db.models import Sandbox as SandboxModel
from api.app.models.sandbox import SandboxCreateRequest
from api.app.models.common import generate_id
from api.app.repositories.base import BaseRepository


class SandboxRepository(BaseRepository[SandboxModel, SandboxCreateRequest, dict]):
    """Repository for Sandbox operations"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(SandboxModel, session)
    
    async def get_by_workspace(self, workspace_id: str) -> list[SandboxModel]:
        """Get all sandboxes for a workspace"""
        return await self.list(workspace_id=workspace_id)
    
    async def create_sandbox(
        self, 
        sandbox_in: SandboxCreateRequest, 
        workspace_id: str
    ) -> SandboxModel:
        """Create new sandbox"""
        import json
        
        sandbox_data = {
            "sandbox_id": generate_id("sb"),
            "workspace_id": workspace_id,
            "name": sandbox_in.name,
            "status": "provisioning",
            "agent_config_json": json.dumps(sandbox_in.agent_config.model_dump()),
            "connection_details_json": None,
            "container_id": None,
        }
        
        db_obj = SandboxModel(**sandbox_data)
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        
        return db_obj
    
    async def update_status(self, sandbox_id: str, status: str) -> SandboxModel | None:
        """Update sandbox status"""
        from sqlalchemy import update
        from api.app.db.models import Sandbox
        
        stmt = (
            update(Sandbox)
            .where(Sandbox.sandbox_id == sandbox_id)
            .values(status=status)
        )
        await self.session.execute(stmt)
        await self.session.flush()
        
        return await self.get(sandbox_id)
