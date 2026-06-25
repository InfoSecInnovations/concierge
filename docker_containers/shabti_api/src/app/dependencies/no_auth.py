class NoAuth:
    def __init__(self, scope: str = "read"):
        self.scope = scope

    async def __call__(self):
        return True
