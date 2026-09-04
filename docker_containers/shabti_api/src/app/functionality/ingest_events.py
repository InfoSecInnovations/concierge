"""What an ingest's worker reports as it runs.

Its own module so the insert functions never import the registry: they yield these, and the registry
is what turns them into item state and, from there, into the lines a client reads.

Each one is an idempotent state update for one item rather than a delta, which is what lets the
registry coalesce them per subscriber without anything being lost.
"""

from dataclasses import dataclass
from shabti_types import DocumentIngestError, DocumentIngestInfo


@dataclass(frozen=True)
class ItemQueued:
    """An item the request didn't know about, discovered mid-ingest - a zip's members."""

    item_id: str
    label: str


@dataclass(frozen=True)
class ItemProgress:
    item_id: str
    info: DocumentIngestInfo


@dataclass(frozen=True)
class ItemFailed:
    item_id: str
    error: DocumentIngestError


type IngestEvent = ItemQueued | ItemProgress | ItemFailed
