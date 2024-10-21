from dataclasses import dataclass, field


@dataclass
class CollectionsData:
    collections: list = field(default_factory=list)
    loading: bool = False
