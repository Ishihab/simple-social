from collections.abc import AsyncGenerator
from typing import Annotated, Any
from uuid import UUID

import structlog
from fastapi import Depends, Request, Response
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import AuthenticationBackend, CookieTransport
from fastapi_users.authentication.strategy.db import (
    AccessTokenDatabase,
    DatabaseStrategy,
)
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from fastapi_users_db_sqlalchemy.access_token import SQLAlchemyAccessTokenDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.db import AsyncSessionLocal
from models import AccessToken, User
from schemas import UserCreate

logger = structlog.get_logger()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def get_user_db(session: Annotated[AsyncSession, Depends(get_async_session)]):
    yield SQLAlchemyUserDatabase(session, User)


async def get_access_token_db(
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    yield SQLAlchemyAccessTokenDatabase(session, AccessToken)


class UserManager(UUIDIDMixin, BaseUserManager[User, UUID]):
    reset_password_token_secret = settings.SECRET_KEY
    verification_token_secret = settings.SECRET_KEY

    async def validate_password(self, password: str, user: UserCreate | User) -> None:
        if len(password) < 8:
            raise ValueError("Password should be at least 8 characters")
        if user.username.lower() in password.lower():
            raise ValueError("Password should not contain the username")
        if user.display_name.lower() in password.lower():
            raise ValueError("Password should not contain the display name")

    async def on_after_register(self, user: User, request: Request | None = None):
        logger.info(f"User {user.id} has registered.", user_id=str(user.id))

    async def on_after_login(
        self,
        user: User,
        request: Request | None = None,
        response: Response | None = None,
    ) -> None:
        logger.info(f"User {user.id} has logged in.", user_id=str(user.id))

    async def on_after_update(
        self, user: User, update_dict: dict[str, Any], request: Request | None = None
    ) -> None:
        logger.info(f"User {user.id} has updated their profile.", user_id=str(user.id))

    async def on_after_forgot_password(
        self, user: User, token: str, request: Request | None = None
    ):
        logger.info(
            f"User {user.id} has requested a password reset token.",
            user_id=str(user.id),
        )

    async def on_after_request_verify(
        self, user: User, token: str, request: Request | None = None
    ):
        logger.info(f"Verification requested for user {user.id}.", user_id=str(user.id))

    async def on_after_verify(self, user: User, request: Request | None = None):
        logger.info(f"User {user.id} has been verified.", user_id=str(user.id))


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)


cookie_transport = CookieTransport(
    cookie_name="access_token",
    cookie_max_age=settings.COOKIE_MAX_AGE,
    cookie_secure=False,
    cookie_httponly=True,
    cookie_samesite="lax",
)


def get_database_strategy(
    access_token_db: Annotated[
        AccessTokenDatabase[AccessToken], Depends(get_access_token_db)
    ],
):
    return DatabaseStrategy(access_token_db, lifetime_seconds=settings.COOKIE_MAX_AGE)


auth_backend = AuthenticationBackend(
    name="cookie",
    transport=cookie_transport,
    get_strategy=get_database_strategy,
)

fastapi_users = FastAPIUsers[User, UUID](
    get_user_manager,
    [auth_backend],
)

non_binded_current_active_user = fastapi_users.current_user(active=True)
non_binded_current_active_user_optional = fastapi_users.current_user(
    active=True, optional=True
)
non_binded_current_super_user = fastapi_users.current_user(active=True, superuser=True)


async def get_current_active_user(
    user: Annotated[User, Depends(non_binded_current_active_user)],
):
    structlog.contextvars.bind_contextvars(user_id=str(user.id))
    return user


async def get_current_active_user_optional(
    user: Annotated[User | None, Depends(non_binded_current_active_user_optional)],
):
    if user:
        structlog.contextvars.bind_contextvars(user_id=str(user.id))
    return user


async def get_current_super_user(
    user: Annotated[User, Depends(non_binded_current_super_user)],
):
    structlog.contextvars.bind_contextvars(user_id=str(user.id))
    return user


current_active_user = Annotated[User, Depends(get_current_active_user)]
current_active_user_optional = Annotated[
    User | None, Depends(get_current_active_user_optional)
]
current_super_user = Annotated[User, Depends(get_current_super_user)]

session = Annotated[AsyncSession, Depends(get_async_session)]
