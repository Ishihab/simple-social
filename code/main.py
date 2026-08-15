import asyncio
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi_pagination import add_pagination

from api.dependency import auth_backend, fastapi_users
from api.route.auth import router as auth_router
from api.route.comments import router as comments_router
from api.route.likes import router as likes_router
from api.route.posts import router as posts_router
from api.route.uploads import router as uploads_router
from api.route.users import router as users_router
from core.config import settings
from jobs import register_jobs
from logging_config import setup_logging
from metrics import instrumentator
from middleware import add_structlog_middleware
from schemas import UserCreate, UserRead, UserUpdate


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    loop.set_debug(True)
    loop.slow_callback_duration = 0.1
    setup_logging(json_logs=settings.LOG_JSON_FORMAT, log_level=settings.LOG_LEVEL)
    scheduler = AsyncIOScheduler()
    register_jobs(scheduler)
    scheduler.start()
    try:
        yield
    finally:
        print("Shutting down scheduler...")
        scheduler.shutdown()


app = FastAPI(lifespan=lifespan)
add_structlog_middleware(app)

app.mount("/static", StaticFiles(directory="static"), name="static")


app.include_router(auth_router, prefix="/auth")
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_verify_router(UserRead), prefix="/auth", tags=["auth"]
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)
app.include_router(users_router)
app.include_router(posts_router)
app.include_router(comments_router)
app.include_router(likes_router)
app.include_router(uploads_router)
add_pagination(app)
app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/cookie", tags=["auth"]
)

app.include_router(
    fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"]
)


@app.get("/healthz", response_class=HTMLResponse)
async def health_check():
    return HTMLResponse(content="OK", status_code=200)


instrumentator.instrument(app).expose(app)
