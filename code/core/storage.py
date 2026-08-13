import boto3
import structlog
from botocore.config import Config
from botocore.exceptions import ClientError

from core.config import settings

logger = structlog.get_logger()
s3_client = boto3.client(
    "s3",
    region_name=settings.REGION_NAME,
    config=Config(
        signature_version="s3v4",
        s3={"addressing_style": "virtual"},
    ),
)


def get_presigned_url(
    object_key: str,
    object_type: str,
    expiration: int = 60 * 5,
    bucket_name: str = settings.BUCKET_NAME,
    client=s3_client,
) -> str | None:

    try:
        response = client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": bucket_name,
                "Key": object_key,
                "ContentType": object_type,
            },
            ExpiresIn=expiration,
        )
    except ClientError as e:
        logger.error(f"Error generating presigned URL for object {object_key}: {e}")
        return None
    return response


def delete_objects_from_s3(
    objects: list[dict[str, str]],
    client=s3_client,
    bucket_name: str = settings.BUCKET_NAME,
) -> list | None:
    try:
        response = client.delete_objects(
            Bucket=bucket_name,
            Delete={"Objects": objects},
        )
        deleted = response.get("Deleted", [])
        errors = response.get("Errors", [])
        if errors:
            logger.error(f"Errors occurred while deleting objects: {errors}")
        logger.info(f"Successfully deleted objects: {deleted}")
        return deleted
    except ClientError as e:
        logger.error(e)
        return None
