from fastapi import APIRouter, Depends
from document_collections import get_collections
from fastapi.security import OAuth2AuthorizationCodeBearer, HTTPAuthorizationCredentials
from typing import Annotated
from authentication import server_url

oauth_2_scheme = OAuth2AuthorizationCodeBearer(
    tokenUrl=f"{server_url()}/realms/concierge/protocol/openid-connect/token",
    authorizationUrl=f"{server_url()}/realms/concierge/protocol/openid-connect/auth",
    refreshUrl=f"{server_url()}/realms/concierge/protocol/openid-connect/token",
)

router = APIRouter()


@router.get("/collections")
async def get_collections_route(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(oauth_2_scheme)],
):
    return await get_collections(credentials)
