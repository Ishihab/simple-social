from pathlib import Path
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import crud
from api.dependency import current_active_user, session
from exception import DatabaseReadError, DatabaseWriteError

logger = structlog.get_logger()


router = APIRouter(tags=["likes"])
TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.post("/posts/{post_id}/like", response_class=HTMLResponse)
async def like_post(
    request: Request,
    post_id: UUID,
    session: session,
    current_user: current_active_user,
):
    try:
        post_exists, is_liked, like_count = await crud.like_post(
            session, post_id, current_user.id
        )
    except DatabaseWriteError:
        raise HTTPException(status_code=500, detail="Could not like post")
    except DatabaseReadError:
        raise HTTPException(status_code=500, detail="Could not read post like status")
    if not post_exists:
        logger.info("Post not found for like action", post_id=str(post_id))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )
    logger.info(
        "Post like status updated",
        post_id=str(post_id),
        is_liked=is_liked,
        like_count=like_count,
    )
    return templates.TemplateResponse(
        request=request,
        name="partials/like_button.html",
        context={
            "request": request,
            "post_id": post_id,
            "is_liked": is_liked,
            "likes_count": like_count,
        },
    )
