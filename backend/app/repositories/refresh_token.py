import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update

from app.models import RefreshToken
from app.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def revoke(self, token: RefreshToken, replaced_by: RefreshToken | None = None) -> None:
        token.revoked_at = datetime.now(UTC)
        if replaced_by is not None:
            token.replaced_by_token_id = replaced_by.id
        await self.db.flush()

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> int:
        """Revokes every active token for a user (logout-everywhere /
        reuse-detection response). Returns the number of tokens revoked.
        """
        result = await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        return result.rowcount
