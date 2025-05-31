from typing import Any


class ShabtiRequestError(Exception):
    def __init__(self, status_code, message: Any = ""):
        self.status_code = status_code
        self.message = {"status_code": status_code, "message": message}
        super().__init__(self.message)
