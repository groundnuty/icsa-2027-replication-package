"""Listing traces (T, T-unpaginated, D): did the run's listing stop short, and who stopped it.

Input: the `kind: "list"` lines of the proxy log (DESIGN.md, "Trace schemas").
Each carries the request's `limit` and `token` as sent and the response's
`is_last`, `next_token` and `entries`. Only successful GET requests count; a
HEAD delivers no entries.

For the cause code `truncated_listing` (#17, attributed to `client` or
`agent`), per listed directory:
- a listing is *complete* when some chain of pages, starting from a request
  without a token and following each returned `next_token`, ends on a page
  with `is_last == true`;
- otherwise it is *truncated* if any page said `is_last == false`; its
  unused continuations are the `next_token` values of such pages that no
  later request sent back;
- attribution (#17 comment): `agent` when the requests say so by call site (`caller`,
  from the in-process hook: the agent's own code made a request) or some request carried a
  `token` and paging still stopped; otherwise `client` (the client returned a first page
  and never asked for the next).

Like the read extents, this feeds cause codes only, never the label.
"""
from __future__ import annotations

import dataclasses
from collections.abc import Iterable


@dataclasses.dataclass
class DirListing:
    path: str
    requests: int                    # successful GET listing requests
    requests_with_token: int
    pages_seen: int                  # distinct (limit, token) pages
    entries_listed: int              # entries along the longest followed chain
    complete: bool                   # a chain reached is_last == true
    truncated: bool                  # not complete, and some page said is_last == false
    unused_continuations: int        # next_token values of non-last pages never sent back
    attribution: str | None          # "client" | "agent" when truncated, else None
    dir_size: int | None = None      # known directory size, if given
    failed_requests: int = 0         # non-200 listing requests (e.g. 400 beyond the max limit)

    def to_json(self) -> dict:
        return dataclasses.asdict(self)


def listing_summary(lines: Iterable[dict], dir_sizes: dict[str, int] | None = None) -> dict[str, DirListing]:
    by_dir: dict[str, list[dict]] = {}
    failed: dict[str, int] = {}
    tokens_sent: dict[str, set] = {}      # from every GET, failed ones included: a token sent
    for e in lines:                       # shows the agent (or shim) asked for the next page
        if e.get("kind") != "list" or e.get("method", "GET") != "GET":
            continue
        d = str(e.get("path", "")).strip("/")
        if e.get("token") is not None:
            tokens_sent.setdefault(d, set()).add(e["token"])
        if e.get("status") != 200:
            failed[d] = failed.get(d, 0) + 1
            by_dir.setdefault(d, [])
            continue
        by_dir.setdefault(d, []).append(e)
    out = {}
    for d, reqs in by_dir.items():
        sent = tokens_sent.get(d, set())
        # pages by the token that fetched them (None: a first page)
        pages: dict[object, list[dict]] = {}
        for r in reqs:
            pages.setdefault(r.get("token"), []).append(r)

        memo: dict[object, tuple[int, bool]] = {}

        def from_token(nt, seen):
            """Best (entries, reaches is_last) over the pages fetched with token nt.
            Memoised per token, so a directory listed many times stays linear."""
            if nt in memo:
                return memo[nt]
            if nt is None or nt not in pages or nt in seen:
                return 0, False
            best = (0, False)
            for nxt in pages[nt]:
                m, k = chain_from(nxt, seen | {nt})
                if (k, m) > (best[1], best[0]):
                    best = (m, k)
            memo[nt] = best
            return best

        def chain_from(r, seen):
            """Entries along the chain that starts at page r, and whether it ends on is_last."""
            n, ok = int(r.get("entries") or 0), bool(r.get("is_last"))
            if ok:
                return n, True
            m, k = from_token(r.get("next_token"), seen)
            return n + m, k

        best_n, complete = 0, False
        for r in pages.get(None, []):
            n, k = chain_from(r, frozenset())
            if (k, n) > (complete, best_n):
                best_n, complete = n, k
        unused = {r.get("next_token") for r in reqs
                  if r.get("is_last") is False and r.get("next_token") is not None} - sent
        truncated = not complete and any(r.get("is_last") is False for r in reqs)
        attribution = None
        if truncated:
            attribution = "agent" if sent or any(r.get("caller") == "agent" for r in reqs) else "client"
        out[d] = DirListing(
            path=d, requests=len(reqs), requests_with_token=sum(r.get("token") is not None for r in reqs),
            pages_seen=len({(r.get("limit"), r.get("token")) for r in reqs}), entries_listed=best_n,
            complete=complete, truncated=truncated, unused_continuations=len(unused),
            attribution=attribution, dir_size=(dir_sizes or {}).get(d), failed_requests=failed.get(d, 0))
    return out


def listing_from_http(http_lines: Iterable[dict], ids: dict[str, str] | None = None,
                      dir_sizes: dict[str, int] | None = None) -> dict[str, DirListing]:
    """The summary from the in-process listing stream (hooks: requests.Session.send). A real
    request names its directory by Onedata file id, resolved through `ids` (full index); a
    directory the index does not know keeps its id."""
    lines = []
    for r in http_lines:
        d = r.get("dir") if r.get("dir") is not None else (ids or {}).get(r.get("dir_id"), r.get("dir_id"))
        lines.append(dict(r, path=d))
    return listing_summary(lines, dir_sizes)
