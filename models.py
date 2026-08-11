from datetime import datetime
from uuid import UUID, uuid4
from core.db import Base

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, engine, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID
from fastapi_users_db_sqlalchemy.access_token import SQLAlchemyBaseAccessTokenTableUUID


class User(SQLAlchemyBaseUserTableUUID, Base):
    username: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(50))
    avatar_url: Mapped[str | None] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(
        default=func.now()
    )
    bio: Mapped[str | None] = mapped_column(Text)

    posts: Mapped[list["Post"]] = relationship(back_populates="author", cascade="all, delete-orphan")
    comments: Mapped[list["Comment"]] = relationship(back_populates="author", cascade="all, delete-orphan")
    likes: Mapped[list["Like"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    followers: Mapped[list["Follow"]] = relationship(
        foreign_keys="[Follow.followee_id]",
        back_populates="followee",
        cascade="all, delete-orphan",
    )
    following: Mapped[list["Follow"]] = relationship(
        foreign_keys="[Follow.follower_id]",
        back_populates="follower",
        cascade="all, delete-orphan",
    )
    

class Post(Base):
    __tablename__ = "posts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(String(280))
    image_url: Mapped[str | None] = mapped_column(Text, index=True)
    likes_count: Mapped[int] = mapped_column(Integer, default=0)
    comments_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    author: Mapped["User"] = relationship(back_populates="posts")
    comments: Mapped[list["Comment"]] = relationship(back_populates="post", cascade="all, delete-orphan", order_by="Comment.created_at.desc()")
    likes: Mapped[list["Like"]] = relationship(back_populates="post", cascade="all, delete-orphan")



class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    post_id: Mapped[UUID] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    post: Mapped["Post"] = relationship(back_populates="comments")
    author: Mapped["User"] = relationship(back_populates="comments")

class Like(Base):
    __tablename__ = "likes"

    post_id: Mapped[UUID] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    post: Mapped["Post"] = relationship(back_populates="likes")
    user: Mapped["User"] = relationship(back_populates="likes")


class Follow(Base):
    __tablename__ = "follows"

    follower_id: Mapped[UUID] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), primary_key=True, index=True)
    followee_id: Mapped[UUID] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    follower: Mapped["User"] = relationship(foreign_keys=[follower_id], back_populates="following")
    followee: Mapped["User"] = relationship(foreign_keys=[followee_id], back_populates="followers")

class ObjectStoreObject(Base):
    __tablename__ = "object_store_objects"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    file_key: Mapped[str] = mapped_column(String, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())


class AccessToken(SQLAlchemyBaseAccessTokenTableUUID, Base):
    pass



