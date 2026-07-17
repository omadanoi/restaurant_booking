from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, ConflictError
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models import RefreshToken, User
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.auth import TokenPair
from app.schemas.user import UserCreate

logger = get_logger(__name__)


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)
        self.settings = get_settings()

    async def register(self, data: UserCreate) -> User:
        existing = await self.users.get_by_email(data.email)
        if existing is not None:
            raise ConflictError("An account with this email already exists.")

        user = await self.users.create(
            {
                "email": data.email,
                "hashed_password": hash_password(data.password),
                "full_name": data.full_name,
                "phone": data.phone,
            }
        )
        logger.info(
            "user_registered",
            extra={"extra_fields": {"user_id": str(user.id), "email": user.email}},
        )
        return user

    async def login(self, email: str, password: str, user_agent: str | None = None) -> TokenPair:
        user = await self.users.get_by_email(email)
        # Verify against a dummy hash even when the user doesn't exist, so
        # response timing doesn't reveal which emails are registered.
        if user is None:
            verify_password(password, hash_password("timing-equalizer"))
            logger.warning("login_failed", extra={"extra_fields": {"email": email, "reason": "unknown_email"}})
            raise AuthenticationError("Incorrect email or password.")

        if not verify_password(password, user.hashed_password):
            logger.warning(
                "login_failed",
                extra={"extra_fields": {"user_id": str(user.id), "reason": "bad_password"}},
            )
            raise AuthenticationError("Incorrect email or password.")

        if not user.is_active:
            logger.warning(
                "login_failed",
                extra={"extra_fields": {"user_id": str(user.id), "reason": "inactive"}},
            )
            raise AuthenticationError("This account has been deactivated.")

        pair = await self._issue_token_pair(user, user_agent)
        logger.info("login_succeeded", extra={"extra_fields": {"user_id": str(user.id)}})
        return pair

    async def refresh(self, raw_refresh_token: str, user_agent: str | None = None) -> TokenPair:
        token = await self.refresh_tokens.get_by_hash(hash_refresh_token(raw_refresh_token))
        if token is None:
            raise AuthenticationError("Invalid refresh token.")

        if token.revoked_at is not None:
            # Reuse of a rotated-out token = likely theft. Kill the whole family.
            revoked = await self.refresh_tokens.revoke_all_for_user(token.user_id)
            logger.warning(
                "refresh_token_reuse_detected",
                extra={
                    "extra_fields": {
                        "user_id": str(token.user_id),
                        "tokens_revoked": revoked,
                    }
                },
            )
            raise AuthenticationError("Invalid refresh token.")

        if token.expires_at <= datetime.now(timezone.utc):
            raise AuthenticationError("Refresh token has expired.")

        user = await self.users.get(token.user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("User not found or inactive.")

        pair, new_token = await self._issue_token_pair_with_record(user, user_agent)
        await self.refresh_tokens.revoke(token, replaced_by=new_token)
        return pair

    async def logout(self, raw_refresh_token: str) -> None:
        """Revokes the presented refresh token. Idempotent: unknown or
        already-revoked tokens are a no-op, so logout never fails.
        """
        token = await self.refresh_tokens.get_by_hash(hash_refresh_token(raw_refresh_token))
        if token is not None and token.revoked_at is None:
            await self.refresh_tokens.revoke(token)
            logger.info("logout", extra={"extra_fields": {"user_id": str(token.user_id)}})

    async def _issue_token_pair(self, user: User, user_agent: str | None) -> TokenPair:
        pair, _ = await self._issue_token_pair_with_record(user, user_agent)
        return pair

    async def _issue_token_pair_with_record(
        self, user: User, user_agent: str | None
    ) -> tuple[TokenPair, RefreshToken]:
        raw_refresh = generate_refresh_token()
        record = await self.refresh_tokens.create(
            {
                "user_id": user.id,
                "token_hash": hash_refresh_token(raw_refresh),
                "expires_at": datetime.now(timezone.utc)
                + timedelta(days=self.settings.REFRESH_TOKEN_EXPIRE_DAYS),
                "user_agent": user_agent,
            }
        )
        access = create_access_token(user.id, user.role.value)
        return TokenPair(access_token=access, refresh_token=raw_refresh), record
