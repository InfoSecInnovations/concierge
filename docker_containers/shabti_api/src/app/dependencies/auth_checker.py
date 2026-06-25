from fastapi import Depends
from typing import Annotated
from ..authorization import (
    authorize,
    UnauthorizedOperationError,
)
from .valid_access_token import valid_access_token


class AuthChecker:
    def __init__(self, scope: str = "read"):
        self.scope = scope

    async def __call__(
        self,
        credentials: Annotated[str, Depends(valid_access_token)],
        collection_id: str,
    ):
        authorized = await authorize(credentials, collection_id, self.scope)
        if not authorized:
            raise UnauthorizedOperationError()
