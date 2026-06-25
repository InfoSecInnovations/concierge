from fastapi import Depends
from typing import Annotated
from shabti_types import (
    PromptInfo,
)
from ..authorization import (
    authorize,
    UnauthorizedOperationError,
)
from .valid_access_token import valid_access_token


class PromptBodyAuthChecker:
    def __init__(self, scope: str = "read"):
        self.scope = scope

    async def __call__(
        self,
        prompt_info: PromptInfo,
        credentials: Annotated[str, Depends(valid_access_token)],
    ):
        authorized = await authorize(credentials, prompt_info.collection_id, self.scope)
        if not authorized:
            raise UnauthorizedOperationError()
