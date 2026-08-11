from api.dependency import current_super_user, session
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from models import User
import structlog
import crud
from fastapi_pagination.cursor import CursorParams, CursorPage


cursor_params = Annotated[CursorParams, Depends()]

logger = structlog.get_logger()

router = APIRouter()

@router.get("/superuser-only")
async def superuser_only_route(current_user: current_super_user):
    if not current_user:
        raise HTTPException(status_code=403, detail="You must be a superuser to access this route.")
    return {"message": "Welcome, superuser!"}

@router.get("/superuser/users")
async def get_all_users(current_user: current_super_user, session: session, cursor_params: cursor_params):
    if not current_user:
        logger.warning(f"Unauthorized access attempt to superuser route by user {current_user.id if current_user else 'unknown'}.")
        raise HTTPException(status_code=403, detail="You must be a superuser to access this route.")
    try:
        users = await crud.get_all_users(session, cursor_params, current_user)
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        raise HTTPException(status_code=500, detail="Could not fetch users")
    logger.info(f"Fetched all users for superuser {current_user.id}.")
    return users