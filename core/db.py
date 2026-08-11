from sqlalchemy.orm import mapped_column, Mapped, DeclarativeBase
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from core.config import settings
import aiosqlite



class Base(DeclarativeBase):
    pass

engine = create_async_engine(settings.DATABASE_URL, echo=False)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


