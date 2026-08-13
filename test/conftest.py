

import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from core.db import Base
from main import app
from api.dependency import get_async_session
from utils import create_user
from core.config import settings
from bs4 import BeautifulSoup

TEST_DATABASE_URL = "sqlite+aiosqlite:///file:testmemdb?mode=memory&cache=shared"
engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=StaticPool,)

test_async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def session_db():
    async with test_async_session_maker() as session:
        yield session

@pytest_asyncio.fixture
async def test_async_session():
    async with test_async_session_maker() as session:
        try:
            yield session
        finally:
            await session.rollback()
            


@pytest_asyncio.fixture
async def async_normal_user_client(test_async_session):
    async def override_get_async_session():
        async with test_async_session_maker() as session:
            try:
                yield session
            finally:
                await session.rollback()
    app.dependency_overrides[get_async_session] = override_get_async_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def async_super_user_client(test_async_session):
    async def override_get_async_session():
        async with test_async_session_maker() as session:
            try:
                yield session
            finally:
                await session.rollback()
    app.dependency_overrides[get_async_session] = override_get_async_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def async_normal_user_2_client(test_async_session):
    async def override_get_async_session():
        async with test_async_session_maker() as session:
            try:
                yield session
            finally:
                await session.rollback()
    app.dependency_overrides[get_async_session] = override_get_async_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest_asyncio.fixture(scope="session")
async def create_test_super_user(session_db):
    return await create_user(
        email=settings.FIRST_SUPERUSER_EMAIL,
        password=settings.FIRST_SUPERUSER_PASSWORD,
        username=settings.FIRST_SUPERUSER_USERNAME,
        display_name=settings.FIRST_SUPERUSER_DISPLAY_NAME,
        is_superuser=True,
        session=session_db
    )

@pytest_asyncio.fixture(scope="session")
async def create_test_user(session_db):
    return await create_user(
        email="normaluser@example.com",
        password="password123",
        username="normaluser",
        display_name="Normal User",
        is_superuser=False,
        session=session_db
    )

@pytest_asyncio.fixture(scope="session")
async def create_test_user_2(session_db):
    return await create_user(
        email="normaluser2@example.com",
        password="password123",
        username="normaluser2",
        display_name="Normal User 2",
        is_superuser=False,
        session=session_db
    )


@pytest_asyncio.fixture
async def authed_normal_user_client(async_normal_user_client, create_test_user):
    login_data = {
        "username": create_test_user.email,
        "password": "password123"
    }
    response = await async_normal_user_client.post("/auth/cookie/login", data=login_data)
    assert response.status_code == 204
    return async_normal_user_client

@pytest_asyncio.fixture
async def authed_user_2_client(async_normal_user_2_client, create_test_user_2):
    login_data = {
        "username": create_test_user_2.email,
        "password": "password123"
    }
    response = await async_normal_user_2_client.post("/auth/cookie/login", data=login_data)
    assert response.status_code == 204
    return async_normal_user_2_client


@pytest_asyncio.fixture
async def authed_user_post(authed_normal_user_client):
    post_data = {
        "content": "This is a test post."
    }
    response = await authed_normal_user_client.post("/posts", data=post_data)
    soup = BeautifulSoup(response.text, 'html.parser')
    post_id = soup.find('div', {'id': 'post_card_body'})['data-post-id']
    comment_response = await authed_normal_user_client.post(f"/posts/{post_id}/comments", data={"content": "This is a test comment."})
    like_response = await authed_normal_user_client.post(f"/posts/{post_id}/like")
    comment_soup = BeautifulSoup(comment_response.text, 'html.parser')
    like_soup = BeautifulSoup(like_response.text, 'html.parser')
    is_liked = like_soup.find('button', {'id': 'like-btn'})['data-response']
    comment_id = comment_soup.find('li', {'data': 'comment-body'})['data-comment-id']
    assert response.status_code == 200
    assert post_id is not None
    return {
        "post_id": post_id,
        "comment_id": comment_id,
        "is_liked": is_liked
    }

