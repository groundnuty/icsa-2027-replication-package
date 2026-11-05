"""Create the study space on ONE provider, upload s1z/ and s2z/sst_s2.nc, verify every file by download+hash.

    uv run python -m icsa.ingest.provision_upload --provider site_g [--space-id ID]   # create (or resume) + upload + verify
    uv run python -m icsa.ingest.provision_upload --provider site_g --space-id ID --verify-only

Run unsandboxed (federation calls). Reuses the Day-0 helpers (od.py / odpw.py / odsafe.py) from
DAY0_SCRIPTS (default: <repo>/day0/scripts), with their change log redirected to
data/upload_changes.jsonl. The Onezone admin password is read by odpw from
~/.secrets/icsa-2027/onedata.pass; no credential is printed or written.

Space: icsa2027_data_<UTC stamp>, supported only by --provider. Layout in the space:
    /<space>/s1z/sst_YYYYMMDD.nc  (15,340)   and   /<space>/s2z/sst_s2.nc
Verification (all from the provider, not from local state):
  * the root holds exactly {s1z, s2z}; s1z holds exactly the manifest names; s2z holds exactly sst_s2.nc;
  * every file is downloaded (S1: whole file; S2: 64 MiB Range blocks, one stream) and its sha256 is
    compared with data/manifest/s{1,2}_sha256.txt; at most --workers (<= 8) concurrent streams.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import threading
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DAY0_SCRIPTS = os.environ.get(      # in-repo helpers; the variable only overrides
    "DAY0_SCRIPTS", str(Path(__file__).resolve().parents[2] / "day0" / "scripts"))
sys.path.insert(0, DAY0_SCRIPTS)
import requests  # noqa: E402
import od  # noqa: E402
import odpw  # noqa: E402,F401  (replaces od's password reader)
import odsafe  # noqa: E402

from icsa.paths import S1Z_DIR, S2Z_FILE  # noqa: E402

CHUNK = 64 << 20
S1_DIRNAME, S2_DIRNAME = "s1z", "s2z"


def read_manifest(p: Path) -> dict[str, str]:
    out = {}
    for line in p.read_text().splitlines():
        d, name = line.split("  ", 1)
        out[name] = d
    return out


RETRY_EVENTS: list[dict] = []     # every retried read of this run (UTC, request, error)
READS = [0]
_LOCK = threading.Lock()


def rop(o, prov, method, path, **kw):
    """o.op for reads, retried on connection errors / timeouts (a read has no side effect)."""
    with _LOCK:
        READS[0] += 1
    for attempt in range(5):
        try:
            return o.op(prov, method, path, **kw)
        except requests.RequestException as e:
            with _LOCK:
                RETRY_EVENTS.append({
                    "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "attempt": attempt + 1,
                    "request": f"{method} {path}" + (f" {kw['headers']['Range']}" if kw.get("headers") else ""),
                    "error": type(e).__name__, "timeout": isinstance(e, requests.Timeout),
                    "detail": str(e)[:160]})
            if attempt == 4:
                raise
            time.sleep(2 * (attempt + 1))


def children(o, prov, dir_id) -> dict[str, dict]:
    out, tok = {}, None
    while True:
        params = {"limit": 1000}
        if tok:
            params["token"] = tok
        j = rop(o, prov, "GET", f"/data/{dir_id}/children", params=params).json()
        for c in j.get("children", []):
            out[c["name"]] = c
        if j.get("isLast", True):
            return out
        tok = j.get("nextPageToken")
        if not tok:
            raise od.ODError("children listing: not last page but no nextPageToken")


def mkdir(o, prov, parent, name) -> str:
    r = o.op(prov, "POST", f"/data/{parent}/children", params={"name": name, "type": "DIR"})
    return r.json()["fileId"]


def put_file(o, prov, parent, path: Path, existing: dict[str, dict]) -> bool:
    """Create + upload one file in 64 MiB blocks. Skips a file already present with the right size."""
    size = path.stat().st_size
    cur = existing.get(path.name)
    if cur is not None:
        if int(o.op(prov, "GET", f"/data/{cur['fileId']}").json()["size"]) == size:
            return False
        raise od.ODError(f"{path.name} exists on the provider with a different size; refusing to overwrite")
    fid = o.op(prov, "POST", f"/data/{parent}/children", params={"name": path.name, "type": "REG"}).json()["fileId"]
    with open(path, "rb") as f:
        off = 0
        while off < size:
            buf = f.read(CHUNK)
            o.op(prov, "PUT", f"/data/{fid}/content", params={"offset": off}, data=buf, timeout=600,
                 headers={"content-type": "application/octet-stream"})
            off += len(buf)
    got = int(o.op(prov, "GET", f"/data/{fid}").json()["size"])
    if got != size:
        raise od.ODError(f"{path.name}: size after upload {got} != {size}")
    return True


def sha_remote(o, prov, fid, size, stream_chunk=CHUNK) -> str:
    h = hashlib.sha256()
    off = 0
    while off < size:
        n = min(stream_chunk, size - off)
        r = rop(o, prov, "GET", f"/data/{fid}/content", headers={"Range": f"bytes={off}-{off + n - 1}"},
                expect=(200, 206), timeout=600)
        if len(r.content) != n:                                   # short read: refetch once before failing
            r = rop(o, prov, "GET", f"/data/{fid}/content", headers={"Range": f"bytes={off}-{off + n - 1}"},
                    expect=(200, 206), timeout=600)
            if len(r.content) != n:
                raise od.ODError(f"short read at {off}: {len(r.content)} != {n}")
        h.update(r.content)
        off += n
    return h.hexdigest()


def check_exclusive_support(o, sid: str, prov: str) -> list[str]:
    """The space must be supported by exactly `prov`; returns the supporting provider ids."""
    sup = sorted((o.oz("GET", f"/user/spaces/{sid}").json().get("providers") or {}))
    if sup != [od.PROVIDERS[prov]["id"]]:
        raise od.ODError(f"space {sid} is supported by {sup}, not only by {prov} ({od.PROVIDERS[prov]['id']})")
    return sup


def verify(o, prov, root, m1: dict, m2: dict, s1_dir: Path, s2_file: Path, workers: int) -> dict:
    top = children(o, prov, root)
    res = {"root_entries": sorted(top)}
    ok = sorted(top) == sorted([S1_DIRNAME, S2_DIRNAME])
    c1 = children(o, prov, top[S1_DIRNAME]["fileId"]) if S1_DIRNAME in top else {}
    c2 = children(o, prov, top[S2_DIRNAME]["fileId"]) if S2_DIRNAME in top else {}
    res.update(s1_count=len(c1), s2_entries=sorted(c2))
    ok = ok and sorted(c1) == sorted(m1) and sorted(c2) == sorted(m2)

    def one(item):
        name, fid, size, want = item
        if int(rop(o, prov, "GET", f"/data/{fid}").json()["size"]) != size:    # trailing extra bytes would not change the hash
            return name, False
        return name, sha_remote(o, prov, fid, size) == want

    items = [(n, c1[n]["fileId"], (s1_dir / n).stat().st_size, m1[n]) for n in sorted(m1) if n in c1]
    items += [(n, c2[n]["fileId"], s2_file.stat().st_size, m2[n]) for n in sorted(m2) if n in c2]
    # S2 is one 3.8 GB sequential stream; run it alongside the S1 pool without exceeding `workers` streams
    s2 = [i for i in items if i[0] == s2_file.name]
    s1 = [i for i in items if i[0] != s2_file.name]
    bad, matched = [], 0
    # one worker is one stream: the S1 pool and S2's stream then take turns (b3 #6)
    sep = workers > 1
    with ThreadPoolExecutor(max(1, workers - 1)) as pool, ThreadPoolExecutor(1) as one_pool:
        f2 = [one_pool.submit(one, i) for i in s2] if sep else [pool.submit(one, i) for i in s2]
        for name, good in pool.map(one, s1):
            matched += good
            if not good:
                bad.append(name)
        for f in f2:
            name, good = f.result()
            matched += good
            if not good:
                bad.append(name)
    res.update(files_expected=len(m1) + len(m2), files_matched=matched, mismatches=sorted(bad))
    res["ok"] = bool(ok and not bad and matched == len(m1) + len(m2))
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", required=True, choices=sorted(od.PROVIDERS))
    ap.add_argument("--space-id")
    ap.add_argument("--size-gb", type=int, default=20, help="support size requested from the provider")
    ap.add_argument("--s1", type=Path, default=S1Z_DIR)
    ap.add_argument("--s2", type=Path, default=S2Z_FILE)
    ap.add_argument("--manifests", type=Path, default=Path("data/manifest"))
    ap.add_argument("--record", type=Path, default=Path("data/upload_record.json"))
    ap.add_argument("--retry-log", type=Path, default=Path("data/upload_retries.jsonl"))
    ap.add_argument("--changes-log", type=Path, default=Path("data/upload_changes.jsonl"))
    ap.add_argument("--verify-only", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args(argv)
    if not 1 <= a.workers <= 8:
        raise SystemExit("--workers must be 1..8")
    od.CHANGES = a.changes_log.resolve()      # od.log_change appends here
    m1, m2 = read_manifest(a.manifests / "s1_sha256.txt"), read_manifest(a.manifests / "s2_sha256.txt")
    if sorted(m1) != sorted(p.name for p in a.s1.glob("*.nc")) or list(m2) != [a.s2.name]:
        raise SystemExit("manifests do not match the local files exactly")
    o = od.OD()
    prov = a.provider
    sid = a.space_id
    created = False
    if sid is None:
        name = "icsa2027_data_" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        sid = odsafe.create_space_owned(o, name)
        created = True
    name = o.oz("GET", f"/spaces/{sid}").json()["name"]
    if not name.startswith("icsa2027_data_"):
        raise SystemExit(f"refusing to use space {sid} named {name!r}")
    print(f"space {name} {sid}", flush=True)
    try:
        if created:
            o.support(sid, prov, a.size_gb * 10**9)
            print(f"support ready after {o.wait_supported(sid, prov):.1f}s", flush=True)
        root = None
        for _ in range(30):
            try:
                root = o.space_root(prov, sid)
                break
            except Exception:
                time.sleep(1)
        if root is None:
            raise od.ODError("space root not available")
        if not a.verify_only:
            top = children(o, prov, root)
            d1 = top[S1_DIRNAME]["fileId"] if S1_DIRNAME in top else mkdir(o, prov, root, S1_DIRNAME)
            d2 = top[S2_DIRNAME]["fileId"] if S2_DIRNAME in top else mkdir(o, prov, root, S2_DIRNAME)
            ex1, ex2 = children(o, prov, d1), children(o, prov, d2)
            files = sorted(a.s1.glob("*.nc"))
            t0 = time.time()
            with ThreadPoolExecutor(a.workers) as pool:
                wrote = sum(pool.map(lambda p: put_file(o, prov, d1, p, ex1), files))
            print(f"s1z: {wrote} written, {len(files) - wrote} already present, {time.time() - t0:.0f}s", flush=True)
            t0 = time.time()
            w2 = put_file(o, prov, d2, a.s2, ex2)
            print(f"s2z: {'written' if w2 else 'already present'}, {time.time() - t0:.0f}s", flush=True)
            od.log_change("data_upload", space_id=sid, name=name, provider=prov, s1_files=len(files),
                          s2_files=1, where=f"{prov} oneprovider POST/PUT /data (s1z/, s2z/)")
        supporters = check_exclusive_support(o, sid, prov)
        t0 = time.time()
        res = verify(o, prov, root, m1, m2, a.s1, a.s2, a.workers)
        res["verify_seconds"] = round(time.time() - t0)
        res["supporting_provider_ids"] = supporters
        res["manifest_sha256"] = {n: hashlib.sha256((a.manifests / f"{n}_sha256.txt").read_bytes()).hexdigest()
                                  for n in ("s1", "s2")}     # binds "verified" to these exact manifests
        res["reads"] = READS[0]
        res["retries"] = len(RETRY_EVENTS)
        res["timeouts"] = sum(e["timeout"] for e in RETRY_EVENTS)
        res["retry_log"] = str(a.retry_log)
        a.retry_log.write_text("".join(json.dumps(e) + "\n" for e in RETRY_EVENTS))
        res["supported_only_by_provider"] = True
    except BaseException:
        print(f"FAILED; the space {sid} ({name}) is kept for resume with --space-id; nothing was torn down", flush=True)
        raise
    rec = {"space_name": name, "space_id": sid, "provider": prov, "provider_id": od.PROVIDERS[prov]["id"],
           "provider_host": od.PROVIDERS[prov]["host"], "space_root_file_id": root,
           "s1_dir": f"/{name}/{S1_DIRNAME}/", "s2_path": f"/{name}/{S2_DIRNAME}/{a.s2.name}",
           "verification": res}
    a.record.write_text(json.dumps(rec, indent=2) + "\n")
    print(json.dumps(res, indent=2))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
