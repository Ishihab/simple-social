from pathlib import Path
from uuid import UUID

import structlog
from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import crud
from api.dependency import current_active_user, session
from exception import DatabaseWriteError

logger = structlog.get_logger()
router = APIRouter(tags=["comments"])
TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.post("/posts/{post_id}/comments", response_class=HTMLResponse)
async def create_comment(
    request: Request,
    post_id: UUID,
    session: session,
    current_user: current_active_user,
    content: str = Form(..., min_length=3, max_length=500),
):
    try:
        comment = await crud.create_comment(session, post_id, current_user.id, content)
    except DatabaseWriteError:
        raise HTTPException(status_code=500, detail="Could not create comment")
    if not comment:
        logger.info("Post not found for comment creation", post_id=str(post_id))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )
    logger.info(
        "Comment created successfully",
        comment_id=str(comment.id),
        post_id=str(post_id),
    )
    return templates.TemplateResponse(
        request=request,
        name="partials/comments.html",
        context={
            "request": request,
            "comment": comment,
            "current_user": current_user,
        },
    )


@router.delete("/posts/{post_id}/comments/{comment_id}", response_class=HTMLResponse)
async def delete_comment(
    post_id: UUID,
    comment_id: UUID,
    session: session,
    current_user: current_active_user,
):
    try:
        success = await crud.delete_comment(
            session, comment_id, current_user.id, current_user.is_superuser
        )
    except DatabaseWriteError:
        raise HTTPException(status_code=500, detail="Could not delete comment")
    if not success:
        logger.info(
            "Comment not found or user unauthorized to delete",
            comment_id=str(comment_id),
            post_id=str(post_id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found or user unauthorized to delete",
        )
    logger.info(
        "Comment deleted successfully",
        comment_id=str(comment_id),
        post_id=str(post_id),
    )

    return HTMLResponse(content="", status_code=status.HTTP_200_OK)
