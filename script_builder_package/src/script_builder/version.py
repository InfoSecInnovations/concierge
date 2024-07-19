class Version:
    def __init__(self, v: str):
        self.v = v
        split = self.v.split(".")
        self.major = int(split[0])
        self.minor = int(split[1])
        self.patch = int(split[2])

    def __gt__(self, other):
        if self.major > other.major:
            return True
        if self.major < other.major:
            return False
        if self.minor > other.minor:
            return True
        if self.minor < other.minor:
            return False
        return self.patch > other.patch

    def __lt__(self, other):
        if self.major < other.major:
            return True
        if self.major > other.major:
            return False
        if self.minor < other.minor:
            return True
        if self.minor > other.minor:
            return False
        return self.patch < other.patch

    def __eq__(self, other):
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
        )

    def __ne__(self, other):
        return not (self == other)

    def __ge__(self, other):
        return self > other or self == other

    def __le__(self, other):
        return self < other or self == other
