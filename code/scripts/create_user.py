import asyncio
import sys
from pathlib import Path
from utils import create_user
from core.config import settings

parent_dir = Path(__file__).resolve().parent.parent

sys.path.append(str(parent_dir))

if __name__ == "__main__":
    asyncio.run(
        create_user(
            email=settings.FIRST_SUPERUSER_EMAIL,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            username=settings.FIRST_SUPERUSER_USERNAME,
            display_name=settings.FIRST_SUPERUSER_DISPLAY_NAME,
            )
        )