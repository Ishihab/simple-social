from pathlib import Path
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi_pagination.cursor import CursorPage, CursorParams

import crud
import schemas
from api.dependency import current_active_user, session
from exception import DatabaseReadError

logger = structlog.get_logger()

cursor_params = Annotated[CursorParams, Depends()]

router = APIRouter(tags=["debug"])
TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/feed", response_model=CursorPage[schemas.PostFeedRead])
async def get_feed(
    request: Request,
    session: session,
    current_user: current_active_user,
    cursor_params: cursor_params,
):
    try:
        posts_page: CursorPage[schemas.PostFeedRead] = await crud.get_feed_posts(
            session, current_user.id, cursor_params
        )
    except DatabaseReadError:
        raise HTTPException(status_code=500, detail="Could not fetch feed posts")
    return posts_page
