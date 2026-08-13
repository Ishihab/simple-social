import time
import uuid

import structlog
from fastapi import FastAPI, Request

logger = structlog.get_logger()


def add_structlog_middleware(app: FastAPI):
    @app.middleware("http")
    async def structlog_middleware(request: Request, call_next):
        structlog.contextvars.clear_contextvars()

        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            http_method=request.method,
            http_request_path=request.url.path,
        )
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.info(
                "request_processed",
                request_id=request_id,
                duration_ms=execution_time_ms,
                status_code=response.status_code,
            )
            return response
        except Exception as e:
            execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception(
                "request_failed",
                duration_ms=execution_time_ms,
                error=str(e),
            )
            raise
