from uuid import UUID
from pathlib import Path
from fastapi.templating import Jinja2Templates
from fastapi import APIRouter, Depends, Form, HTTPException, status, Request
from fastapi.responses import HTMLResponse
import crud
from typing import Annotated
import schemas
from api.dependency import session, current_active_user
from fastapi_pagination.cursor import CursorParams, CursorPage
from exception import DatabaseReadError, DatabaseWriteError
import structlog

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
        posts_page: CursorPage[schemas.PostFeedRead] = await crud.get_feed_posts(session, current_user.id, cursor_params)
    except DatabaseReadError as e:
        raise HTTPException(status_code=500, detail="Could not fetch feed posts")
    return posts_page
    