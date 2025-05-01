class CollectionExistsError(Exception):
    def __init__(self, message=""):
        self.message = message


class InvalidLocationError(Exception):
    def __init__(self, message=""):
        self.message = message


class InvalidUserError(Exception):
    def __init__(self, message=""):
        self.message = message
