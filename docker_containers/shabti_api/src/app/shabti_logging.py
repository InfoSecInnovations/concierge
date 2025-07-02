import logging
from shabti_keycloak import get_token_info


async def log_user_action(token, message, **kwargs):
    logger = logging.getLogger("shabti")
    token_info = await get_token_info(token)
    user_id = token_info["sub"]
    username = token_info["name"]
    logger.info(
        message, extra={"user": {"name": username, "user_id": user_id}, **kwargs}
    )


async def log_action(message, **kwargs):
    logger = logging.getLogger("shabti")
    logger.info(message, extra={**kwargs})
