from typing import Callable

from fastapi.responses import JSONResponse




class AppException(Exception):
    """Base exception for the application."""

    def __init__(self, detail: str, code: str | None = None):
        self.detail = detail
        self.code = code or self.__class__.__name__

class NotFoundException(AppException):
    def __init__(self, detail: str):
        super().__init__(detail, "NotFound")

class UnauthorizedException(AppException):
    def __init__(self, detail: str):
        super().__init__(detail, "Unauthorized")

class ForbiddenException(AppException):
    def __init__(self, detail: str):
        super().__init__(detail, "Forbidden")

class ConflictException(AppException):
    def __init__(self, detail: str):
        super().__init__(detail, "Conflict")

class ValidationException(AppException):
    def __init__(self, detail: str):
        super().__init__(detail, "Validation")



exception_handlers: dict[type[AppException], Callable] = {
    NotFoundException: lambda request, exc: JSONResponse(
        status_code=404,
        content={"detail": exc.detail, "code": exc.code},
    ),
    UnauthorizedException: lambda request, exc: JSONResponse(
        status_code=401,
        content={"detail": exc.detail, "code": exc.code},
    ),
    ForbiddenException: lambda request, exc: JSONResponse(
        status_code=403,
        content={"detail": exc.detail, "code": exc.code},
    ),
    ConflictException: lambda request, exc: JSONResponse(
        status_code=409,
        content={"detail": exc.detail, "code": exc.code},
    ),
    ValidationException: lambda request, exc: JSONResponse(
        status_code=422,
        content={"detail": exc.detail, "code": exc.code},
    ),
}