import asyncio
import sys
from pathlib import Path

from fastapi_users.exceptions import UserAlreadyExists

from core.config import settings
from utils import create_user

parent_dir = Path(__file__).resolve().parent.parent

sys.path.append(str(parent_dir))

if __name__ == "__main__":
    try:
        asyncio.run(
            create_user(
                email=settings.FIRST_SUPERUSER_EMAIL,
                password=settings.FIRST_SUPERUSER_PASSWORD,
                username=settings.FIRST_SUPERUSER_USERNAME,
                display_name=settings.FIRST_SUPERUSER_DISPLAY_NAME,
            )
        )
    except UserAlreadyExists:
        print(f"User with email {settings.FIRST_SUPERUSER_EMAIL} already exists.")
