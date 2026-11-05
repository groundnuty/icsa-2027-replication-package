"""Write the expected-extent metadata on the two dataset roots of the study space (#6).

Production safety on the data provider: this module performs exactly these requests, nothing else.
  GET  /spaces/{sid}                       (read the space name and root id; the name must start icsa2027_data_)
  GET  /data/{root}/children               (find s1z and s2z; read only)
  GET  /data/{s2z}/children                (find sst_s2.nc; read only)
  GET  /data/{id}/metadata/json            (read what is there)
  PUT  /data/{id}/metadata/json            (ONLY for id in {the s1z directory, the sst_s2.nc file}; ONLY if it differs)
It never lists the 15,340-file directory, never touches file content, and logs each PUT in the changes file.
`op` is any callable (method, path, **kw) -> response, so tests drive a fake provider.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

from icsa.records import Layout

from . import extent_meta
from .extent_meta import S1_DIRNAME, S2_DIRNAME

S2_FILENAME = "sst_s2.nc"
SPACE_PREFIX = "icsa2027_data_"

Op = Callable[..., Any]


class WriteRefused(RuntimeError):
    pass


def _children(op: Op, fid: str) -> dict[str, dict]:
    out, tok = {}, None
    while True:
        params: dict = {"limit": 1000}
        if tok:
            params["token"] = tok
        j = op("GET", f"/data/{fid}/children", params=params).json()
        out.update({c["name"]: c for c in j.get("children", [])})
        if j.get("isLast", True):
            return out
        tok = j["nextPageToken"]


def resolve_roots(op: Op, space_name: str, space_id: str) -> dict[Layout, str]:
    """fileIds of the S1 directory and the S2 file. Lists only the space root (2 entries) and s2z (1 entry)."""
    if not space_name.startswith(SPACE_PREFIX):
        raise WriteRefused(f"space {space_name!r} is not an {SPACE_PREFIX}* space")
    root = op("GET", f"/spaces/{space_id}").json()["fileId"]
    top = _children(op, root)
    if sorted(top) != sorted([S1_DIRNAME, S2_DIRNAME]):
        raise WriteRefused(f"space root holds {sorted(top)}, expected exactly {[S1_DIRNAME, S2_DIRNAME]}")
    s2 = _children(op, top[S2_DIRNAME]["fileId"])
    if sorted(s2) != [S2_FILENAME]:
        raise WriteRefused(f"{S2_DIRNAME} holds {sorted(s2)}")
    return {Layout.S1: top[S1_DIRNAME]["fileId"], Layout.S2: s2[S2_FILENAME]["fileId"]}


def write_all(op: Op, space_name: str, space_id: str, docs: dict[Layout, dict],
              log: Callable[..., None], *, dry_run: bool = False) -> dict[str, str]:
    """Set `docs[layout]` as the JSON metadata of each root; verify by reading back. Returns {layout: action}."""
    for layout, doc in docs.items():
        extent_meta.check(doc, layout)
    roots = resolve_roots(op, space_name, space_id)
    allowed = set(roots.values())
    result = {}
    for layout, doc in docs.items():
        fid = roots[layout]
        cur = op("GET", f"/data/{fid}/metadata/json", expect=(200, 400, 404))
        if cur.status_code == 200:
            have = cur.json()
        elif cur.status_code == 404 or "enodata" in json.dumps(cur.json()):   # no JSON metadata yet (Onedata 25.0: 400 + enodata)
            have = None
        else:
            raise WriteRefused(f"reading metadata of {layout.value} root failed: HTTP {cur.status_code} {json.dumps(cur.json())[:200]}")
        if have == doc:
            result[layout.value] = "unchanged"
            continue
        if have not in (None, {}):
            raise WriteRefused(f"{layout.value} root already carries different JSON metadata; refusing to overwrite")
        if dry_run:
            result[layout.value] = "would-write"
            continue
        if fid not in allowed:   # defence in depth; cannot happen unless resolve_roots is changed
            raise WriteRefused(f"{fid} is not a dataset root")
        op("PUT", f"/data/{fid}/metadata/json", json=doc, expect=(200, 201, 204))
        log("knowledge_metadata_write", space_id=space_id, name=space_name, layout=layout.value, file_id=fid,
            where=f"PUT /data/{fid}/metadata/json", bytes=len(json.dumps(doc)))
        back = op("GET", f"/data/{fid}/metadata/json").json()
        if back != doc:
            raise WriteRefused(f"read-back of {layout.value} differs from what was written")
        result[layout.value] = "written"
    return result


def main(argv: list[str] | None = None) -> int:
    import argparse
    import os
    import sys
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--provider", default="site_g")
    ap.add_argument("--space-id", required=True)
    ap.add_argument("--changes-log", type=Path, required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    sys.path.insert(0, os.environ.get("DAY0_SCRIPTS", str(Path(__file__).resolve().parents[2] / "day0" / "scripts")))
    import od  # noqa: E402
    import odpw  # noqa: E402,F401  (admin password from the persistent secret file)
    od.CHANGES = a.changes_log.resolve()
    o = od.OD()
    name = o.oz("GET", f"/spaces/{a.space_id}").json()["name"]
    docs = {lay: json.loads(extent_meta.frozen_path(lay).read_text()) for lay in (Layout.S1, Layout.S2)}
    res = write_all(lambda m, p, **kw: o.op(a.provider, m, p, **kw), name, a.space_id, docs, od.log_change,
                    dry_run=a.dry_run)
    print(json.dumps({"space": name, "provider": a.provider, "result": res, "utc": time.strftime("%FT%TZ", time.gmtime())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
