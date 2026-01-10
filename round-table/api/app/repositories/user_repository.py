"""User repository"""

from sqlalchemy.ext.asyncio import AsyncSession

from api.app.db.models import User as UserModel
from api.app.models.auth import RegisterRequest, User
from api.app.repositories.base import BaseRepository


class UserRepository(BaseRepository[UserModel, RegisterRequest, dict]):
    """Repository for User operations"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(UserModel, session)
    
    async def get_by_email(self, email: str) -> UserModel | None:
        """Get user by email"""
        return await self.get_by_field("email", email)
    
    async def create_user(self, user_in: RegisterRequest, hashed_password: str) -> UserModel:
        """Create new user with hashed password"""
        import secrets
        from api.app.models.common import generate_id
        
        user_data = user_in.model_dump()
        user_data["hashed_password"] = hashed_password
        user_data["user_id"] = f"usr_{secrets.token_hex(5)}"
        
        db_obj = UserModel(**user_data)
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        
        return db_obj
