import asyncio
from pathlib import Path
import sys
parent_dir = Path(__file__).resolve().parent.parent

sys.path.append(str(parent_dir))
from utils import create_user
from models import User, Post, Comment, Like, Follow
import faker
import random


from core.db import AsyncSessionLocal

fake = faker.Faker()


async def populate_database(num_users: int, num_posts_per_user: int, num_comments_per_post: int, num_likes_per_post: int):
    users = []
    for _ in range(num_users):
        email = fake.unique.email()
        password = "password123"
        username = fake.pystr(min_chars=5, max_chars=15)
        display_name = fake.name()
        avatar_url = f"https://avatars.githubusercontent.com/u/{random.randint(1, 100000)}"
        user = await create_user(email, password, username, display_name, avatar_url=avatar_url)
        
        users.append(user)
    if not users:
        print("No users created. Exiting.")
        return

    async with AsyncSessionLocal() as session:
        async with session.begin():
            for follower in users:
                for followee in users:
                    if follower != followee:
                        follow = Follow(follower_id=follower.id, followee_id=followee.id)
                        session.add(follow)
            posts = []
            for user in users:
                for _ in range(num_posts_per_user):
                    content = fake.text(max_nb_chars=280)
                    post = Post(author_id=user.id, content=content, image_url=fake.image_url())
                    session.add(post)
                    posts.append(post)
            await session.flush()  # Ensure post.id is available
            for post in posts:
                for _ in range(num_comments_per_post):
                    post_id = post.id
                    author_id = random.choice(users).id
                    content = fake.text(max_nb_chars=500)
                    comment = Comment(post_id=post_id, author_id=author_id, content=content)
                    session.add(comment)
                    post.comments_count += 1
            existing_likes = set()
            for post in posts:
                for _ in range(num_likes_per_post):
                    user_id = random.choice(users).id
                    post_id = post.id
                    if (post_id, user_id) not in existing_likes:
                        like = Like(post_id=post_id, user_id=user_id)
                        session.add(like)
                        existing_likes.add((post_id, user_id))
                        post.likes_count += 1
        await session.commit()

if __name__ == "__main__":
    #asyncio.run(create_user("admin@example.com", "password123", "admin", "Admin User", avatar_url="https://avatars.githubusercontent.com/u/97165289", is_superuser=True))
    num_users = 100
    num_posts_per_user = 20
    num_comments_per_post = 30
    num_likes_per_post = num_users 

    asyncio.run(populate_database(num_users, num_posts_per_user, num_comments_per_post, num_likes_per_post))
                
        