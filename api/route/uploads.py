import mimetypes
import uuid
import structlog
from core.config import settings
from core.storage import get_presigned_url
from api.dependency import current_active_user, session
from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from models import User, ObjectStoreObject
from schemas import PresignResponse
from crud import create_object_store_object_entry
from exception import DatabaseWriteError

logger = structlog.get_logger()

router = APIRouter(tags=["uploads"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

@router.post("/presign", response_model=PresignResponse)
async def get_presigned_upload_url(
    content_type: str,
    file_name: str,
    current_user: current_active_user,
    session: session,
):
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid content type")
    bucket_name = settings.BUCKET_NAME
    file_extension = mimetypes.guess_extension(content_type) or ".bin"
    
    unique_file_key = f"posts/{current_user.id}/{uuid.uuid4()}{file_extension}"
    public_url = f"https://{bucket_name}.s3.{settings.REGION_NAME}.amazonaws.com/{unique_file_key}"
    try:
        presigned_url = await run_in_threadpool(get_presigned_url,
            bucket_name=bucket_name,
            object_key=unique_file_key,
            object_type=content_type,
            expiration=60 * 5,  # URL valid for 5 minutes
        )
    except Exception as e:
        logger.error(f"Error generating presigned URL: {e}", content_type=content_type, file_name=file_name)
        raise HTTPException(status_code=500, detail="Could not generate presigned URL")
    try:
        object_store_object = await create_object_store_object_entry(
            session=session,
            file_key=unique_file_key,
        )
    except DatabaseWriteError as e:
        logger.error(f"Error creating object store entry", file_key=unique_file_key)
        raise HTTPException(status_code=500, detail="Could not create object store entry")
    logger.info(f"Object store entry created successfully", file_key=unique_file_key, object_id=str(object_store_object.id))
    logger.info(f"Presigned URL generated successfully", file_key=unique_file_key)
    return PresignResponse(
        upload_url=presigned_url,
        public_url=public_url,
        object_key=unique_file_key,
    )
    
