from sqlalchemy.orm import mapped_column, Mapped, DeclarativeBase
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from core.config import settings
import asyncpg

DATABASE_URL = str(settings.SQLALCHEMY_DATABASE_URI)

class Base(DeclarativeBase):
    pass

engine = create_async_engine(DATABASE_URL, echo=True)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


