"""The one full layout index: every S1 file and S2, with the Onedata file ids (#9).

    python -m icsa.instruments.fullindex [--ids]        # once, outside the sandbox

A run may read any file of the dataset, so labelling needs all of them: a read of a file the index
does not hold is an unidentified source, and the run unknown. Built once from the local copy (#3,
byte-identical to site_g), for the files of #3's manifests, and stored under ICSA_DATA/layout with the
digest of those manifests; `load_full_index` refuses it if the manifests changed. The file ids map
the gate log's content paths to files (crosscheck.py) and are read from site_g, read-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from ..paths import DATA_ROOT
from .layout import LayoutIndex, build_layout

REPO = Path(__file__).resolve().parents[2]
MANIFESTS = (REPO / "data" / "manifest" / "s1_sha256.txt", REPO / "data" / "manifest" / "s2_sha256.txt")
S1, S2 = "s1z", "s2z"


def manifest_digest() -> str:
    h = hashlib.sha256()
    for p in MANIFESTS:
        h.update(p.name.encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


def manifest_files(root: Path) -> list[Path]:
    """The dataset's files, as #3 names them; sizes are checked against totals.json on building."""
    def names(p):
        return [line.split()[-1] for line in p.read_text().splitlines() if line.strip()]
    return [root / S1 / n for n in names(MANIFESTS[0])] + [root / S2 / n for n in names(MANIFESTS[1])]


def fetch_ids(oneprovider: str, space: str, token: str, *, page: int = 1000, session=None) -> dict[str, str]:
    """{file id: path relative to the space} of the dataset's directories and files, from
    the provider's REST API: read-only, one listing per directory."""
    import requests
    s = session or requests.Session()
    s.headers.update({"X-Auth-Token": token})
    base = f"https://{oneprovider}/api/v3/oneprovider"

    def lookup(rel):
        r = s.post(f"{base}/lookup-file-id/{space}/{rel}".rstrip("/"), timeout=60)
        r.raise_for_status()
        return r.json()["fileId"]

    out = {lookup(""): ""}                 # the space's root: an agent may list it too
    for d in (S1, S2):
        did = lookup(d)
        out[did] = d
        token_ = None
        while True:
            q = {"limit": page, "attribute": ["name", "file_id"]}      # Onedata 25.0's names, probed on site_g
            if token_:
                q["token"] = token_
            r = s.get(f"{base}/data/{did}/children", params=q, timeout=120)
            r.raise_for_status()
            js = r.json()
            for c in js["children"]:
                out[c["file_id"]] = f"{d}/{c['name']}"
            if js.get("isLast", True):
                break
            token_ = js["nextPageToken"]
    return out


def _one(args):
    return build_layout(Path(args[0]), Path(args[1]))


def index_dir(root: Path | None = None) -> Path:
    return Path(root or DATA_ROOT) / "layout"


def build(root: Path | None = None, *, ids: dict[str, str] | None = None, workers: int = 2) -> Path:
    root = Path(root or DATA_ROOT)
    files = manifest_files(root)
    missing = [str(f) for f in files if not f.is_file()]
    if missing:
        raise FileNotFoundError(f"{len(missing)} files of #3's manifests are missing, e.g. {missing[0]}")
    totals = json.loads((REPO / "data" / "manifest" / "totals.json").read_text())
    n1 = sum(f.stat().st_size for f in files[:-1])
    n2 = files[-1].stat().st_size
    if (n1, n2) != (totals["s1"]["bytes"], totals["s2"]["bytes"]):
        raise ValueError(f"local sizes {n1}, {n2} differ from #3's totals {totals}")
    with ProcessPoolExecutor(workers) as ex:
        layouts = list(ex.map(_one, [(str(f), str(root)) for f in files], chunksize=200))
    out = index_dir(root)
    out.mkdir(parents=True, exist_ok=True)
    LayoutIndex({fl.relpath: fl for fl in layouts}).save(out / "index.npz")
    (out / "ids.json").write_text(json.dumps(ids or {}))
    (out / "digest.json").write_text(json.dumps({"manifest_sha256": manifest_digest(), "files": len(files),
                                                 "ids": len(ids or {})}, indent=1))
    return out


def load_full_index(root: Path | None = None) -> LayoutIndex:
    """The stored full index, its ids on `.ids`. Fails loudly if it is missing, is of other
    manifests, or holds another number of files; there is no partial fallback."""
    d = index_dir(root)
    digest = d / "digest.json"
    if not digest.is_file():
        raise FileNotFoundError(f"no full layout index at {d}: run python -m icsa.instruments.fullindex")
    rec = json.loads(digest.read_text())
    if rec["manifest_sha256"] != manifest_digest():
        raise ValueError(f"the index at {d} was built from other manifests: rebuild it")
    index = LayoutIndex.load(d / "index.npz", shas_from_caller=True)      # the file holds none: from the manifests, below
    if len(index) != rec["files"]:
        raise ValueError(f"the index at {d} holds {len(index)} files, its digest says {rec['files']}")
    index.ids = json.loads((d / "ids.json").read_text())
    # Every file and directory needs its Onedata id: the gate log names content by id, and a file without one
    # would look delivered by nobody (a false decoded_not_delivered) and leave listings keyed by bare ids.
    missing = (set(index.layouts) | {"", S1, S2}) - set(index.ids.values())
    if missing:
        raise ValueError(f"the index at {d} has no Onedata ids for {len(missing)} of its files and directories "
                         f"(e.g. {sorted(missing)[0]!r}): rebuild it with --ids")
    index.shas = manifest_shas()
    index.require_shas(d / "index.npz")
    return index


def manifest_shas() -> dict[str, str]:
    """sha256 -> path, from #3's manifests (the files are byte-identical to site_g's)."""
    out = {}
    for p, sub in zip(MANIFESTS, (S1, S2)):
        for line in p.read_text().splitlines():
            if line.strip():
                digest, name = line.split()[0], line.split()[-1]
                out[digest] = f"{sub}/{name}"
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", type=Path, default=None)
    ap.add_argument("--ids", action="store_true", help="read the file ids from site_g (read-only)")
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args(argv)
    ids = None
    if a.ids:
        from ..harness.oracle_real import PROVIDER_HOST, SPACE_NAME, mint_token
        ids = fetch_ids(PROVIDER_HOST, SPACE_NAME, mint_token(oneclient=False))
    print(build(a.root, ids=ids, workers=a.workers))
    return 0


if __name__ == "__main__":
    sys.exit(main())
