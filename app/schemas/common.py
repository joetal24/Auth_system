from pydantic import BaseModel


class ErrorResponse(BaseModel):
    detail: str
    code: str


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int = 1
    size: int = 20