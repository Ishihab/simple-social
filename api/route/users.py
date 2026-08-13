from pathlib import Path
from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi_pagination.cursor import CursorPage, CursorParams

import crud
import schemas
from api.dependency import current_active_user, current_active_user_optional, session
from exception import DatabaseReadError, DatabaseWriteError

logger = structlog.get_logger()

router = APIRouter(tags=["users"])
TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
async def root(
    request: Request,
    session: session,
    current_user: current_active_user_optional,
):
    if current_user is None:
        return templates.TemplateResponse(
            request=request,
            name="pages/auth/login.html",
            context={"request": request},
        )
    return RedirectResponse(url="/feed", status_code=status.HTTP_302_FOUND)


@router.get("/users/profile/{user_id}", response_class=HTMLResponse)
async def get_user_profile(
    request: Request,
    user_id: UUID,
    session: session,
    current_user: current_active_user,
):
    try:
        user_profile = await crud.get_user_profile(session, user_id, current_user.id)
        current_user_profile = await crud.get_user_profile(
            session, current_user.id, current_user.id
        )
        current_user_followers: CursorPage[schemas.UserRead] = await crud.get_followers(
            session, current_user.id, CursorParams()
        )
        current_user_following: CursorPage[schemas.UserRead] = await crud.get_following(
            session, current_user.id, CursorParams()
        )
        user_posts: CursorPage[schemas.PostFeedRead] = await crud.get_user_posts(
            session, user_id, CursorParams()
        )
        liked_post_ids = await crud.get_liked_post_ids(
            session, current_user.id, [post.id for post in user_posts.items]
        )
    except DatabaseReadError:
        raise HTTPException(status_code=500, detail="Could not fetch user profile")
    if not user_profile:
        logger.info(f"User not found for id {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    logger.info("Fetched user profile", profile_user_id=str(user_id))
    return templates.TemplateResponse(
        request=request,
        name="pages/profile.html",
        context={
            "request": request,
            "profile": user_profile,
            "current_user": current_user_profile,
            "posts": user_posts.items,
            "liked_ids": liked_post_ids,
            "current_user_followers": current_user_followers.items,
            "current_user_following": current_user_following.items,
            "next_page": user_posts.next_page,
        },
    )


@router.get("/settings", response_class=HTMLResponse)
async def get_user_settings(
    request: Request,
    session: session,
    current_user: current_active_user,
):
    return templates.TemplateResponse(
        request=request,
        name="pages/settings.html",
        context={
            "request": request,
            "current_user": current_user,
        },
    )


@router.post("/users/{user_id}/follow", response_class=HTMLResponse)
async def follow_user(
    request: Request,
    user_id: UUID,
    session: session,
    current_user: current_active_user,
):
    if current_user.id == user_id:
        logger.info(f"User {current_user.id} attempted to follow themselves.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot follow yourself.",
        )
    try:
        is_self, is_following = await crud.follow_user(
            session, followee_id=user_id, follower_id=current_user.id
        )
    except DatabaseWriteError:
        raise HTTPException(status_code=500, detail="Could not follow user")
    except DatabaseReadError:
        raise HTTPException(status_code=500, detail="Could not check follow status")

    if is_self:
        logger.info(f"User {current_user.id} attempted to follow themselves.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot follow yourself.",
        )
    logger.info(
        f"User {current_user.id} followed user {user_id}.",
        follower_id=str(current_user.id),
        followee_id=str(user_id),
    )
    return templates.TemplateResponse(
        request=request,
        name="partials/follow_button.html",
        context={
            "request": request,
            "is_following": is_following,
            "user_id": user_id,
            "current_user": current_user,
        },
    )


@router.get("/users/{user_id}/followers", response_class=HTMLResponse)
async def get_followers(
    user_id: UUID,
    session: session,
    current_user: current_active_user,
    cursor: Annotated[CursorParams, Depends()] = CursorParams(),
):
    try:
        followers: CursorPage[schemas.UserRead] = await crud.get_followers(
            session, user_id, cursor
        )
    except DatabaseReadError:
        raise HTTPException(status_code=500, detail="Could not fetch followers")
    if followers is None:
        logger.info(f"User not found for id {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    logger.info(f"Fetched followers for user {user_id}.")

    html_content = "<h1>Followers</h1><ul>"
    for follower in followers.items:
        html_content += f"<li>{follower.username} ({follower.email})</li>"
    html_content += "</ul>"
    # html_content += f"<p>Page {followers.page} of {followers.total_pages}</p>"
    html_content += f"<p>Total followers: {followers.total}</p>"
    html_content += f"<p>Current cursor: {followers.current_page}</p>"
    html_content += f"<p>Next cursor: {followers.next_page}</p>"
    html_content += f"<p>Previous cursor: {followers.previous_page}</p>"
    html_content += f"<p>Current page backward: {followers.current_page_backwards}</p>"

    return HTMLResponse(content=html_content, status_code=status.HTTP_200_OK)


@router.get("/users/{user_id}/following", response_class=HTMLResponse)
async def get_following(
    user_id: UUID,
    session: session,
    current_user: current_active_user,
    cursor: Annotated[CursorParams, Depends()] = CursorParams(),
):
    try:
        following: CursorPage[schemas.UserRead] = await crud.get_following(
            session, user_id, cursor
        )
    except DatabaseReadError:
        raise HTTPException(status_code=500, detail="Could not fetch following")
    if following is None:
        logger.info(f"User not found for id {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    logger.info(f"Fetched following for user {user_id}.")
    html_content = "<h1>Following</h1><ul>"
    for followee in following.items:
        html_content += f"<li>{followee.username} ({followee.email})</li>"
    html_content += "</ul>"
    # html_content += f"<p>Page {following.page} of {following.total_pages}</p>"
    html_content += f"<p>Current cursor: {following.current_page}</p>"
    html_content += f"<p>Next cursor: {following.next_page}</p>"
    html_content += f"<p>Previous cursor: {following.previous_page}</p>"
    html_content += f"<p>Current page backward: {following.current_page_backwards}</p>"

    return HTMLResponse(content=html_content, status_code=status.HTTP_200_OK)
