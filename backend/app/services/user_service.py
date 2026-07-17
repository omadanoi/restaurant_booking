from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.repositories.user import UserRepository


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.users = UserRepository(db)

    async def list_users(self, limit: int, offset: int) -> tuple[list[User], int]:
        items = await self.users.list(limit=limit, offset=offset)
        total = await self.users.count()
        return items, total
