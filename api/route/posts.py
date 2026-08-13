from pathlib import Path
from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi_pagination.cursor import CursorPage, CursorParams

import crud
import schemas
from api.dependency import current_active_user, session
from exception import DatabaseReadError, DatabaseWriteError

logger = structlog.get_logger()

cursor_params = Annotated[CursorParams, Depends()]

router = APIRouter(tags=["posts"])
TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/feed", response_class=HTMLResponse)
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
        current_user_profile = await crud.get_user_profile(
            session, current_user.id, current_user.id
        )
        liked_post_ids = await crud.get_liked_post_ids(
            session, current_user.id, [post.id for post in posts_page.items]
        )
    except DatabaseReadError:
        raise HTTPException(status_code=500, detail="Could not fetch feed posts")
    if request.headers.get("HX-Request") != "true":
        try:
            current_user_followers: CursorPage[
                schemas.UserRead
            ] = await crud.get_followers(session, current_user.id, cursor_params)
            current_user_following: CursorPage[
                schemas.UserRead
            ] = await crud.get_following(session, current_user.id, cursor_params)
        except DatabaseReadError:
            raise HTTPException(
                status_code=500, detail="Could not fetch followers/following"
            )
        current_user_followers.items = current_user_followers.items[:5]
        current_user_following.items = current_user_following.items[:5]
    logger.info("Fetched feed posts", post_count=len(posts_page.items))
    if request.headers.get("HX-Request") == "true":
        return templates.TemplateResponse(
            request=request,
            name="partials/post_list.html",
            context={
                "request": request,
                "posts": posts_page.items,
                "liked_ids": liked_post_ids,
                "current_user": current_user_profile,
                "current_user.superuser": current_user.is_superuser,
                "next_page": posts_page.next_page,
            },
        )
    return templates.TemplateResponse(
        request=request,
        name="pages/feed.html",
        context={
            "request": request,
            "posts": posts_page.items,
            "liked_ids": liked_post_ids,
            "current_user": current_user_profile,
            "current_user.superuser": current_user.is_superuser,
            "current_user_followers": current_user_followers.items,
            "current_user_following": current_user_following.items,
            "next_page": posts_page.next_page,
        },
    )


@router.get("/users/{user_id}/posts", response_class=HTMLResponse)
async def get_user_posts(
    request: Request,
    user_id: UUID,
    session: session,
    cursor_params: cursor_params,
    current_user: current_active_user,
):
    try:
        posts_page: CursorPage[schemas.PostFeedRead] = await crud.get_user_posts(
            session, user_id, cursor_params
        )
    except DatabaseReadError:
        raise HTTPException(status_code=500, detail="Could not fetch user posts")
    logger.info(
        "Fetched user posts", user_id=str(user_id), post_count=len(posts_page.items)
    )
    return templates.TemplateResponse(
        request=request,
        name="pages/post_detail.html",
        context={
            "request": request,
            "posts": posts_page.items,
            "next_page": posts_page.next_page,
        },
    )


@router.get("/posts/{post_id}", response_class=HTMLResponse)
async def get_post(
    request: Request,
    post_id: UUID,
    session: session,
    current_user: current_active_user,
):
    try:
        post = await crud.get_post(session, post_id, current_user.id)
        current_user_profile = await crud.get_user_profile(
            session, current_user.id, current_user.id
        )
    except DatabaseReadError:
        raise HTTPException(status_code=500, detail="Could not fetch post")
    if not post:
        logger.info("Post not found", post_id=str(post_id))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )
    logger.info("Fetched post", post_id=str(post_id))
    return templates.TemplateResponse(
        request=request,
        name="pages/post_detail.html",
        context={
            "request": request,
            "post": post,
            "current_user": current_user_profile,
            "current_user.is_superuser": current_user.is_superuser,
        },
    )


@router.post("/posts", response_class=HTMLResponse)
async def create_post(
    request: Request,
    session: session,
    current_user: current_active_user,
    content: str = Form(..., min_length=1, max_length=280),
    image_url: str | None = Form(None),
):
    try:
        post = await crud.create_post(session, current_user.id, content, image_url)
    except DatabaseWriteError:
        raise HTTPException(status_code=500, detail="Could not create post")
    logger.info("Post created successfully", post_id=str(post.id))
    return templates.TemplateResponse(
        request=request,
        name="partials/post_card.html",
        context={
            "request": request,
            "post": post,
            "current_user": current_user,
        },
    )


@router.delete("/posts/{post_id}", response_class=HTMLResponse)
async def delete_post(
    post_id: UUID,
    session: session,
    current_user: current_active_user,
):
    try:
        success = await crud.delete_post(
            session, post_id, current_user.id, current_user.is_superuser
        )
    except DatabaseWriteError:
        raise HTTPException(status_code=500, detail="Could not delete post")
    if not success:
        logger.info("Post not found for deletion", post_id=str(post_id))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )
    logger.info("Post deleted successfully", post_id=str(post_id))

    return HTMLResponse(content="", status_code=200)
