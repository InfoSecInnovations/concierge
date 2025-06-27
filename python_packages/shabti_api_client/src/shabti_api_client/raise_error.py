from httpx import Response
from .exceptions import ShabtiRequestError
from shabti_types import CollectionExistsError


def raise_error(response: Response):
    body = response.json()
    if response.status_code >= 400:  # 400 and above are errors
        if "error_type" in body:
            if body["error_type"] == "CollectionExistsError":
                raise CollectionExistsError(
                    body["collection_name"],
                    body["message"],
                    body["location"] if "location" in body else None,
                )
    raise ShabtiRequestError(status_code=response.status_code, message=body)
