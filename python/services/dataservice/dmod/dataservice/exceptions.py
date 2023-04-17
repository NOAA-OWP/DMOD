from typing import Optional
from .errors import Error as ErrorEnum


class ErrorResponseException(Exception):
    def __init__(self, error: ErrorEnum, detail: Optional[str] = None):
        self.error = error
        self.detail = detail or error.detail
