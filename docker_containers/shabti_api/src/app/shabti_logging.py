import logging
from shabti_keycloak import get_token_info
from shabti_types import UserInfo
import os


def logging_enabled():
    return os.getenv("SHABTI_LOGGING_ENABLED") == "True"


async def get_actor(token) -> UserInfo | None:
    """Who a request is on behalf of, decoded once so the token itself needn't be held onto.

    An ingest outlives its request now, and there is no reason to keep a user's bearer token in
    process memory for the hours a crawl can take.
    """
    if token is None:
        return None
    token_info = await get_token_info(token)
    # `name` is the claim the audit log has always used, but it is optional and a service account
    # token does without it, so fall back rather than failing the request that carries one
    username = (
        token_info.get("name")
        or token_info.get("preferred_username")
        or token_info["sub"]
    )
    return UserInfo(username=username, user_id=token_info["sub"])


def log_user_action_as(actor: UserInfo, action, message, **kwargs):
    if not logging_enabled():
        return
    logger = logging.getLogger("shabti")
    logger.info(
        message,
        extra={
            "action": action,
            "user": {"name": actor.username, "user_id": actor.user_id},
            **kwargs,
        },
    )


async def log_user_action(token, action, message, **kwargs):
    if not logging_enabled():
        return
    log_user_action_as(await get_actor(token), action, message, **kwargs)


async def log_action(action, message, **kwargs):
    if not logging_enabled():
        return
    logger = logging.getLogger("shabti")
    logger.info(message, extra={"action": action, **kwargs})
