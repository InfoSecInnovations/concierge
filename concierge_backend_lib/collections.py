from concierge_util import load_config
from typing import Literal
from .authorization import authorize, create_resource
from .authentication import get_token_info
from uuid import uuid4
from .opensearch import create_collection_index
import traceback

config = load_config()
auth_enabled = config and "auth" in config and config["auth"]


class CollectionExistsError(Exception):
    def __init__(self, message):
        self.message = message


class UnauthorizedOperationError(Exception):
    def __init__(self, message):
        self.message = message


def get_collections():
    pass


type Location = Literal["private", "shared"]


def create_collection(token, display_name: str, location: Location):
    try:
        print(f"creating {location} collection {display_name}")
        # TODO: check if we already have a collection with same name and location
        if auth_enabled:
            authorized = authorize(token, f"collection:{location}:create")
            if not authorized:
                raise UnauthorizedOperationError()
            token_info = get_token_info(token)
            owner = token_info["preferred_username"]
            resource_id = create_resource(display_name, f"collection:{location}", owner)
        else:
            resource_id = uuid4()
        create_collection_index(resource_id)
        print(f"created {location} collection {display_name} with ID {resource_id}")
    except Exception:
        traceback.print_exc()


def delete_collection():
    pass


def get_documents():
    pass


def delete_documents():
    pass
