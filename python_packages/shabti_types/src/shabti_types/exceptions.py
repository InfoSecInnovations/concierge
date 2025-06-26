class CollectionExistsError(Exception):
    def __init__(self, collection_name, message=""):
        self.message = message
        self.collection_name = collection_name


class InvalidLocationError(Exception):
    def __init__(self, message=""):
        self.message = message


class InvalidUserError(Exception):
    def __init__(self, message=""):
        self.message = message
