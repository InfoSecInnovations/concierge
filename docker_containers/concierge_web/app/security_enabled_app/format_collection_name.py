from concierge_types import AuthzCollectionInfo

def format_collection_name(collection_info: AuthzCollectionInfo, user_info):
    if collection_info.location == "shared":
        return collection_info.collection_name
    user_id = user_info["sub"]
    if collection_info.owner.user_id == user_id:
        return f"{collection_info.collection_name} (private)"
    return f"{collection_info.collection_name} (private, belongs to {collection_info.owner.username})"