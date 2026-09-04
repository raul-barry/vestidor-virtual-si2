from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.responses import error_response


class AppException(Exception):
    def __init__(self, message: str, status_code: int = 400, error: str | None = None) -> None:
        self.message = message
        self.status_code = status_code
        self.error = error


async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(message=exc.message, error=exc.error),
    )
