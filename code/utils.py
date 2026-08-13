from contextlib import asynccontextmanager

import structlog
from botocore.exceptions import ClientError
from fastapi.concurrency import run_in_threadpool
from fastapi_users.exceptions import UserAlreadyExists
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependency import get_async_session, get_user_db, get_user_manager
from core.storage import delete_objects_from_s3
from crud import orphaned_object_keys, remove_orphaned_objects
from schemas import UserCreate

logger = structlog.get_logger()


get_async_session_context = asynccontextmanager(get_async_session)
get_user_db_context = asynccontextmanager(get_user_db)
get_user_manager_context = asynccontextmanager(get_user_manager)


async def create_user(
    email: str,
    password: str,
    username: str,
    display_name: str,
    avatar_url: str | None = None,
    is_superuser: bool = False,
    session: AsyncSession | None = None,
):
    async def _create(session):
        async with (
                    get_user_db_context(session) as user_db,
                    get_user_manager_context(user_db) as user_manager,
                ):
                user_create = UserCreate(
                    email=email,
                    password=password,
                    is_superuser=is_superuser,
                    username=username,
                    display_name=display_name,
                    avatar_url=avatar_url,
                )
                user = await user_manager.create(user_create)
                print(f"User {user.id} created successfully.")
                return user

    try:
        if session is not None:
            return await _create(session)
        else:
            async with get_async_session_context() as local_session:
                return await _create(local_session)

    except UserAlreadyExists:
        print(f"User with email {email} already exists.")
        raise


async def delete_orphaned_objects(session: AsyncSession):
    orphaned_keys = await orphaned_object_keys(session)
    max_batch_size = 1000
    if orphaned_keys:
        keys_to_delete = [{"Key": key} for key in orphaned_keys]
        for i in range(0, len(orphaned_keys), max_batch_size):
            batch_keys = keys_to_delete[i : i + max_batch_size]
            deleted = await run_in_threadpool(
                delete_objects_from_s3, objects=batch_keys
            )
            if deleted:
                logger.info(
                    f"Deleted {len(deleted)} orphaned objects from S3.",
                    deleted_count=len(batch_keys),
                )
                try:
                    await remove_orphaned_objects(
                        session, [key["Key"] for key in batch_keys]
                    )
                except ClientError as e:
                    logger.error(f"Error removing orphaned objects from database: {e}")


async def delete_orphaned_objects_util():
    try:
        async with get_async_session_context() as session:
            await delete_orphaned_objects(session)
    except ClientError as e:
        logger.error(f"Error deleting orphaned objects: {e}")
