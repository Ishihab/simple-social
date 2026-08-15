from datetime import datetime
from uuid import UUID

from fastapi_users import schemas as users_schemas
from pydantic import BaseModel, Field


class AuthorBrief(BaseModel):
    id: UUID
    username: str
    display_name: str
    avatar_url: str | None = None
    model_config = {
        "from_attributes": True,
    }


class UserRead(users_schemas.BaseUser[UUID]):
    username: str
    display_name: str
    avatar_url: str | None = None
    created_at: datetime
    bio: str | None = None
    model_config = {  # noqa: RUF012
        "from_attributes": True,
    }


class UserCreate(users_schemas.BaseUserCreate):
    username: str = Field(..., min_length=3, max_length=20, pattern=r"^[a-zA-Z0-9_]+$")
    display_name: str = Field(..., min_length=3, max_length=50)
    avatar_url: str | None = None


class UserUpdate(users_schemas.BaseUserUpdate):
    display_name: str | None = Field(None, min_length=3, max_length=50)
    bio: str | None = Field(None, max_length=300)
    avatar_url: str | None = None


class UserProfile(BaseModel):
    id: UUID
    username: str
    display_name: str
    avatar_url: str | None = None
    bio: str | None = None
    followers_count: int
    following_count: int
    followers: list[AuthorBrief] = []
    following: list[AuthorBrief] = []
    posts_count: int
    is_following: bool
    model_config = {
        "from_attributes": True,
    }


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=500)


class CommentRead(BaseModel):
    id: UUID
    post_id: UUID
    author: AuthorBrief
    content: str
    created_at: datetime
    model_config = {
        "from_attributes": True,
    }


class PostCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=280)
    img_url: str | None = None


class PostRead(BaseModel):
    id: UUID
    content: str
    img_url: str | None = None
    author: AuthorBrief
    created_at: datetime
    comments_count: int
    likes_count: int
    comments: list[CommentRead] = []
    model_config = {
        "from_attributes": True,
    }


class PostFeedRead(BaseModel):
    id: UUID
    content: str
    img_url: str | None = None
    author: AuthorBrief
    likes_count: int
    comments_count: int
    created_at: datetime
    model_config = {
        "from_attributes": True,
    }


class FollowRead(BaseModel):
    id: UUID
    follower_id: UUID
    followee_id: UUID
    created_at: datetime
    user_details: AuthorBrief
    model_config = {
        "from_attributes": True,
    }


class PresignResponse(BaseModel):
    upload_url: str
    public_url: str
    object_key: str
