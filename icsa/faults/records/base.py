"""One normalised access event, whatever record it came from, and the parser registry.

Parsers are separate per record (the record definitions are final: audit log, Traefik access log with Range, oneclient perf log). Each
parser turns a record's text into `AccessEvent`s and nothing else; it never sees a scenario.
"""
from __future__ import annotations

import dataclasses
import enum
from typing import Callable, Protocol


class Record(str, enum.Enum):
    AUDIT = "audit"        # (a) op-worker file-access audit log: file level, default-off
    TRAEFIK = "traefik"    # (b) Traefik access log keeping path + Range (T, D); switched on
    PERF = "perf"          # (b) oneclient --log-read-write-perf CSV (M); switched on


class Kind(str, enum.Enum):
    OPEN = "open"
    READ = "read"          # content read: audit remote_read, REST content GET, perf FsLogic read
    RELEASE = "release"
    PREFETCH = "prefetch"  # perf ReadCache prefetch rows: never a client read
    LIST = "list"
    OTHER = "other"


@dataclasses.dataclass(frozen=True)
class AccessEvent:
    ts: float | None              # epoch seconds, UTC
    kind: Kind
    target: str | None            # path (audit, perf) or REST file id (traefik)
    alt_target: str | None = None # audit: file_uuid
    offset: int | None = None     # perf only
    length: int | None = None     # perf only: bytes asked of the client
    status: int | None = None     # traefik only: HTTP status of the response
    range_header: str | None = None
    content_size: int | None = None   # traefik: body bytes sent
    client: str | None = None     # audit: user id; traefik: ClientHost; perf: sidecar id
    record: Record = Record.AUDIT
    raw: str = ""
    user_agent: str | None = None  # traefik: request User-Agent
    run_key: str | None = None    # traefik: the per-run header X-ICSA-Run, added outside the agent container
    request: str | None = None    # audit: the logged request type, verbatim (e.g. proxyio_request::remote_read)


@dataclasses.dataclass(frozen=True)
class ParseResult:
    events: list[AccessEvent]
    n_lines: int
    n_bad: int                    # lines that did not match the record's format (a parser raises above its max_bad)
    n_untimed: int                # events with no usable timestamp
    bad_lines: tuple = ()         # the audit parser's non-matching lines, for what can still be read of them (`audit.salvage`)


class RecordFormatError(ValueError):
    """More lines than a parser's `max_bad` did not match the record's format: a format drift, never a quiet drop."""


class RecordParser(Protocol):
    def __call__(self, text: str, **kw) -> ParseResult: ...


PARSERS: dict[Record, RecordParser] = {}


def register(rec: Record) -> Callable[[RecordParser], RecordParser]:
    def deco(fn: RecordParser) -> RecordParser:
        PARSERS[rec] = fn
        return fn
    return deco
