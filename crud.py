from uuid import UUID
from sqlalchemy import select, case, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload
from fastapi_pagination.cursor import CursorParams, CursorPage
from fastapi_pagination.ext.sqlalchemy import paginate
from models import User, Post, Comment, Like, Follow, ObjectStoreObject
import schemas
from datetime import datetime, timedelta, timezone
from exception import DatabaseWriteError, DatabaseReadError
import structlog

logger = structlog.get_logger()








async def get_feed_posts(session: AsyncSession, user_id: UUID, cursor_params: CursorParams) -> CursorPage[schemas.PostFeedRead]:
    following_subquery = select(Follow.followee_id).where(Follow.follower_id == user_id)
    priority_sort = case(
        (Post.author_id == user_id, 0), 
        (Post.author_id.in_(following_subquery), 1),  
        else_=2  
    )

    query = (
        select(Post)
        .order_by(
            priority_sort.asc(),
            Post.created_at.desc(),
            Post.id.desc()
        )
        .options(selectinload(Post.author))
    )
    try:
        return await paginate(session, query, params=cursor_params)
    except SQLAlchemyError as e:
        logger.exception("Failed to get feed posts", operation="get_feed_posts", user_id=str(user_id))
        raise DatabaseReadError(f"Failed to load feed posts") 

async def get_post(session: AsyncSession, post_id: UUID, user_id: UUID) -> Post | None:
    query = (
        select(Post)
        .where(Post.id == post_id)
        .options(
            selectinload(Post.author),
            selectinload(Post.comments).selectinload(Comment.author)
        )
    )
    try:
        result = await session.execute(query)
    except SQLAlchemyError as e:
        logger.exception("Failed to get post", operation="get_post", post_id=str(post_id), user_id=str(user_id))
        raise DatabaseReadError(f"Failed to load post") 
    return result.scalar_one_or_none()

async def create_post(session: AsyncSession, author_id: UUID, content: str, img_url: str | None) -> Post:
    new_post = Post(author_id=author_id, content=content, image_url=img_url)
    session.add(new_post)
    try:
        await session.commit()
    except SQLAlchemyError as e:
        logger.exception("Failed to create post", operation="create_post", user_id=str(author_id))
        await session.rollback()
        raise DatabaseWriteError(f"Failed to create post") 
    await session.refresh(new_post)
    return new_post

async def delete_post(session: AsyncSession, post_id: UUID, user_id: UUID, superuser: bool) -> bool:
    if superuser:
        query = delete(Post).where(Post.id == post_id)
    else:
        query = delete(Post).where(Post.id == post_id, Post.author_id == user_id)
    try:
        result = await session.execute(query)
        await session.commit()
    except SQLAlchemyError as e:
        logger.exception("Failed to delete post", operation="delete_post", post_id=str(post_id), user_id=str(user_id))
        await session.rollback()
        raise DatabaseWriteError(f"Failed to delete post") 
    return result.rowcount > 0

async def get_user_posts(session: AsyncSession, user_id: UUID, cursor_params: CursorParams) -> CursorPage[schemas.PostFeedRead]:
    query = (
        select(Post)
        .where(Post.author_id == user_id)
        .order_by(Post.created_at.desc(), Post.id.desc())
        .options(selectinload(Post.author))
    )
    try:
        return await paginate(session, query, params=cursor_params)
    except SQLAlchemyError as e:
        logger.exception("Failed to get user posts", operation="get_user_posts", user_id=str(user_id))
        raise DatabaseReadError(f"Failed to load user posts") 


async def create_comment(session: AsyncSession, post_id: UUID, author_id: UUID, content: str) -> schemas.CommentRead | None:
    try:
        post = await session.get(Post, post_id)
    except SQLAlchemyError as e:
        logger.exception("Failed to get post for comment creation", operation="create_comment", post_id=str(post_id), user_id=str(author_id))
        raise DatabaseReadError(f"Could not find post") 
    if post is None:
        return None  

    
    new_comment = Comment(post_id=post_id, author_id=author_id, content=content)
    session.add(new_comment)
    post.comments_count += 1
    try:
        await session.commit()
    except SQLAlchemyError as e:
        logger.exception("Failed to create comment", operation="create_comment", post_id=str(post_id), user_id=str(author_id))
        await session.rollback()
        raise DatabaseWriteError(f"Failed to create comment") 
    await session.refresh(new_comment)
    return schemas.CommentRead(
        id=new_comment.id,
        post_id=new_comment.post_id,
        author=schemas.AuthorBrief(
            id=new_comment.author.id,
            username=new_comment.author.username,
            display_name=new_comment.author.display_name,
            avatar_url=new_comment.author.avatar_url
        ),
        content=new_comment.content,
        created_at=new_comment.created_at,
    )
    


async def delete_comment(session: AsyncSession, comment_id: UUID, user_id: UUID, superuser: bool) -> bool:
    try:   
        comment = await session.get(Comment, comment_id)
    except SQLAlchemyError as e:
        logger.exception("Failed to get comment for deletion", operation="delete_comment", comment_id=str(comment_id), user_id=str(user_id))
        raise DatabaseReadError(f"Could not find comment") 
    if comment is None or (comment.author_id != user_id and not superuser):
        return False
    try:
        post = await session.get(Post, comment.post_id)
    except SQLAlchemyError as e:
        logger.exception("Failed to get post for comment deletion", operation="delete_comment", comment_id=str(comment_id), user_id=str(user_id))
        raise DatabaseReadError(f"Could not find associated post") 
    if post:
        post.comments_count -= 1
    try:
        await session.delete(comment)
        await session.commit()
    except SQLAlchemyError as e:
        logger.exception("Failed to delete comment", operation="delete_comment", comment_id=str(comment_id), user_id=str(user_id))
        await session.rollback()
        raise DatabaseWriteError(f"Failed to delete comment") 
    return True

async def like_post(session: AsyncSession, post_id: UUID, user_id: UUID) -> tuple[bool, bool, int]:
    try:
        post = await session.get(Post, post_id)
    except SQLAlchemyError as e:
        logger.exception("Failed to get post for like/unlike", operation="like_post", post_id=str(post_id), user_id=str(user_id))
        raise DatabaseReadError(f"Could not find post") 
    if post is None:
        return False, False, 0
    try:
        existing_like = await session.get(Like, (post_id, user_id))
    except SQLAlchemyError as e:
        logger.exception("Failed to check existing like", operation="like_post", post_id=str(post_id), user_id=str(user_id))
        raise DatabaseReadError(f"Could not check existing like") 
    if existing_like:
        try:
            await session.delete(existing_like)
            post.likes_count = max(post.likes_count - 1, 0)
            is_liked = False
        except SQLAlchemyError as e:
            logger.exception("Failed to delete existing like", operation="like_post", post_id=str(post_id), user_id=str(user_id))
            await session.rollback()
            raise DatabaseWriteError(f"Failed to delete existing like") 
    else:
        session.add(Like(post_id=post_id, user_id=user_id))
        post.likes_count += 1
        is_liked = True
    try:
        await session.commit()
    except SQLAlchemyError as e:
        logger.exception("Failed to commit like/unlike transaction", operation="like_post", post_id=str(post_id), user_id=str(user_id))
        await session.rollback()
        raise DatabaseWriteError(f"Failed to like/unlike post") 
    return post is not None, is_liked, post.likes_count

async def get_liked_post_ids(session: AsyncSession, user_id: UUID, post_ids: list[UUID]) -> set[UUID]:
    if not post_ids:
        return set()
    query = select(Like.post_id).where(Like.user_id == user_id, Like.post_id.in_(post_ids))
    try:
        result = await session.execute(query)
    except SQLAlchemyError as e:
        logger.exception("Failed to fetch liked post IDs", operation="get_liked_post_ids", user_id=str(user_id), post_ids=[str(pid) for pid in post_ids])
        raise DatabaseReadError(f"Failed to fetch liked post IDs") 
    return set(result.scalars().all())

async def is_following(session: AsyncSession, follower_id: UUID, followee_id: UUID) -> bool:
    try:
        result = await session.get(Follow, {"follower_id": follower_id, "followee_id": followee_id})
        logger.info("Checked follow status", operation="is_following", follower_id=str(follower_id), followee_id=str(followee_id), is_following=result is not None)
    except SQLAlchemyError as e:
        logger.exception("Failed to check follow status", operation="is_following", follower_id=str(follower_id), followee_id=str(followee_id))
        raise DatabaseReadError(f"Failed to check follow status") 
    return result is not None

async def follow_user(session: AsyncSession, follower_id: UUID, followee_id: UUID) -> tuple[bool, bool]:
    # [is_self, is_following]
    if follower_id == followee_id:
        return True, False
    try:
        existing_follow = await session.get(Follow, {"follower_id": follower_id, "followee_id": followee_id})
    except SQLAlchemyError as e:
        logger.exception("Failed to check existing follow", operation="follow_user", follower_id=str(follower_id), followee_id=str(followee_id))
        raise DatabaseReadError(f"Failed to check existing follow") 
    try:
        if existing_follow:
            await session.delete(existing_follow)
            is_following = False
        else:
            session.add(Follow(follower_id=follower_id, followee_id=followee_id))
            is_following = True
        await session.commit()
    except SQLAlchemyError as e:
        logger.exception("Failed to commit follow/unfollow transaction", operation="follow_user", follower_id=str(follower_id), followee_id=str(followee_id))
        await session.rollback()
        raise DatabaseWriteError(f"Failed to follow/unfollow user") 
    return False, is_following

async def get_followers(session: AsyncSession, user_id: UUID, cursor_params: CursorParams) -> CursorPage[schemas.UserRead]:
    query = (
        select(User)
        .join(Follow, Follow.follower_id == User.id)
        .where(Follow.followee_id == user_id)
        .order_by(Follow.created_at.desc(), Follow.follower_id.desc())
    )
    try:
        return await paginate(session, query, params=cursor_params)
    except SQLAlchemyError as e:
        logger.exception("Failed to fetch followers", operation="get_followers", user_id=str(user_id))
        raise DatabaseReadError(f"Failed to fetch followers") 

async def get_following(session: AsyncSession, user_id: UUID, cursor_params: CursorParams) -> CursorPage[schemas.UserRead]:
    query = (
        select(User)
        .join(Follow, Follow.followee_id == User.id)
        .where(Follow.follower_id == user_id)
        .order_by(Follow.created_at.desc(), Follow.followee_id.desc())
    )
    try:
        return await paginate(session, query, params=cursor_params)
    except SQLAlchemyError as e:
        logger.exception("Failed to fetch following", operation="get_following", user_id=str(user_id))
        raise DatabaseReadError(f"Failed to fetch following") 

async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
    query = select(User).where(User.username == username)
    try:
        result = await session.execute(query)
    except SQLAlchemyError as e:
        logger.exception("Failed to fetch user by username", operation="get_user_by_username", username=username)
        raise DatabaseReadError(f"Failed to fetch user by username") 
    return result.scalar_one_or_none()

async def get_user_profile(session: AsyncSession, user_id: UUID, current_user_id: UUID) -> schemas.UserProfile | None:
    user = await session.get(User, user_id)
    if not user:
        return None
    try:
        follower_count = (await session.execute(select(func.count()).select_from(Follow).where(Follow.followee_id == user_id))).scalar_one()
    except SQLAlchemyError as e:
        logger.exception("Failed to fetch follower count", operation="get_user_profile", user_id=str(user_id))
        raise DatabaseReadError(f"Failed to fetch follower count") 
    try:
        following_count = (await session.execute(select(func.count()).select_from(Follow).where(Follow.follower_id == user_id))).scalar_one()
    except SQLAlchemyError as e:
        logger.exception("Failed to fetch following count", operation="get_user_profile", user_id=str(user_id))
        raise DatabaseReadError(f"Failed to fetch following count") 
    try:
        posts_count = (await session.execute(select(func.count()).select_from(Post).where(Post.author_id == user_id))).scalar_one()
    except SQLAlchemyError as e:
        logger.exception("Failed to fetch posts count", operation="get_user_profile", user_id=str(user_id))
        raise DatabaseReadError(f"Failed to fetch posts count") 
    try:
        viewer_is_following = await is_following(session, follower_id=current_user_id, followee_id=user_id)
    except SQLAlchemyError as e:
        logger.exception("Failed to fetch viewer follow status", operation="get_user_profile", user_id=str(user_id), current_user_id=str(current_user_id))
        raise DatabaseReadError(f"Failed to fetch viewer follow status") 
    return schemas.UserProfile(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        bio=user.bio,
        followers_count=follower_count,
        following_count=following_count,
        posts_count=posts_count,
        is_following=viewer_is_following
    )

async def create_object_store_object_entry(session: AsyncSession, file_key: str) -> ObjectStoreObject:
    new_object = ObjectStoreObject(
        file_key=file_key,
    )
    session.add(new_object)
    try:
        await session.commit()
        await session.refresh(new_object)
    except SQLAlchemyError as e:
        logger.exception("Failed to create object store object entry", operation="create_object_store_object_entry", file_key=file_key)
        await session.rollback()
        raise DatabaseWriteError(f"Failed to create object store object entry") 
    return new_object

async def orphaned_object_keys(session: AsyncSession) -> list[str]:
    time_threshold = datetime.now(timezone.utc) - timedelta(hours=1)

    user_avatar_keys_exists = select(1).where(User.avatar_url.contains(ObjectStoreObject.file_key)).exists()
    post_image_keys_exists = select(1).where(Post.image_url.contains(ObjectStoreObject.file_key)).exists()
    query = select(ObjectStoreObject.file_key).where(~user_avatar_keys_exists, ~post_image_keys_exists, ObjectStoreObject.created_at < time_threshold)
    try:
        result = await session.execute(query)
        keys_to_delete = list(result.scalars().all())
        return keys_to_delete
    except SQLAlchemyError as e:
        logger.exception("Failed to fetch orphaned object keys", operation="orphaned_object_keys")
        raise DatabaseReadError(f"Failed to fetch orphaned object keys") 

async def remove_orphaned_objects(session: AsyncSession, keys_to_delete: list[str]) -> None:
    if not keys_to_delete:
        return
    query = delete(ObjectStoreObject).where(ObjectStoreObject.file_key.in_(keys_to_delete))
    try:
        await session.execute(query)
        await session.commit()
    except SQLAlchemyError as e:
        logger.exception("Failed to remove orphaned objects", operation="remove_orphaned_objects", keys_to_delete=keys_to_delete)
        await session.rollback()
        raise DatabaseWriteError(f"Failed to remove orphaned objects") 
    return


async def search_users(session: AsyncSession, query_str: str, cursor_params: CursorParams) -> CursorPage[schemas.UserRead]:
    query = (
        select(User)
        .where(User.username.ilike(f"%{query_str}%"))
        .order_by(User.username.asc())
    )
    try:
        return await paginate(session, query, params=cursor_params)
    except SQLAlchemyError as e:
        logger.exception("Failed to search users", operation="search_users", query_str=query_str)
        raise DatabaseReadError(f"Failed to search users") 

async def search_posts(session: AsyncSession, query_str: str, cursor_params: CursorParams) -> CursorPage[schemas.PostRead]:
    query = (
        select(Post)
        .where(Post.content.ilike(f"%{query_str}%"))
        .order_by(Post.created_at.desc(), Post.id.desc())
        .options(selectinload(Post.author))
    )
    try:
        return await paginate(session, query, params=cursor_params)
    except SQLAlchemyError as e:
        logger.exception("Failed to search posts", operation="search_posts", query_str=query_str)
        raise DatabaseReadError(f"Failed to search posts") 


async def get_all_users(session: AsyncSession, cursor_params: CursorParams, current_user: User) -> CursorPage[schemas.UserRead] | None:
    if not current_user.is_superuser:
        return None  
    query = (
        select(User)
        .order_by(User.username.asc())
    )
    try:
        return await paginate(session, query, params=cursor_params)
    except SQLAlchemyError as e:
        logger.exception("Failed to fetch all users", operation="get_all_users", current_user_id=str(current_user.id))
        raise DatabaseReadError(f"Failed to fetch all users") 

async def delete_user(session: AsyncSession, user_id: UUID, current_user: User) -> bool | None:
    if not current_user.is_superuser:
        return None
    try:
        user = await session.get(User, user_id)
    except SQLAlchemyError as e:
        logger.exception("Failed to fetch user for deletion", operation="delete_user", user_id=str(user_id))
        raise DatabaseReadError(f"Could not find user") 
    if not user:
        return False
    try:
        await session.delete(user)
        await session.commit()
    except SQLAlchemyError as e:
        logger.exception("Failed to delete user", operation="delete_user", user_id=str(user_id))
        await session.rollback()
        raise DatabaseWriteError(f"Failed to delete user")
    return True
