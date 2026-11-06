"""The full layout index of one NEW provider's space (#34, B): the same files as site_g's under other Onedata file ids.

    python -m snapshot.bindex --src-index-root R --out-index-root R2 --provider-host H --space-name S --token-file F

`icsa.instruments.fullindex` holds the index as three files under `<root>/layout/`: `index.npz` (every file's layout, built from the local copy of
the dataset: it says nothing of a provider), `ids.json` (Onedata file id -> path relative to the space: the only provider-specific part, and what the
gate log's content paths are turned into files with) and `digest.json` (the manifests' sha256, the file count and the id count). A space with the
same name on another provider has the same files, so its index is the source index with its OWN `ids.json`, read from that provider's REST API
with `fullindex.fetch_ids(host, space, token)` (read-only: one lookup and listings), and `digest.json` rewritten for the new id count.
Nothing in `icsa/` is changed: `fullindex.main`'s constants stay site_g's, and this takes the host, the space and the token as parameters.

Refused, with nothing written: a source index of other manifests; ids that do not cover exactly the paths of the source's (a path the new space lacks, one
it has more, or two ids for one path); ids that equal the source's (the host or the space resolved to the source's own provider, the silent fallback
this exists to catch; `allow_same_ids` for a rehearsal on a copy); an output that already holds an index. The written index must pass
`fullindex.load_full_index` (every file and directory has an id) or it is removed again. The token is read from a file or the environment and is never
printed, written or put into a message.
The one assumption is the source's `index.npz`: it is copied, so the new space's files must be byte-identical to the source's (they are the dataset of #3).
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse                     # noqa: E402
import json                         # noqa: E402
import os                           # noqa: E402
import shutil                       # noqa: E402
from pathlib import Path           # noqa: E402

from icsa.instruments import fullindex   # noqa: E402

FILES = ("index.npz", "ids.json", "digest.json")


class IndexError_(RuntimeError):
    """The index cannot be built; the message never holds the token."""


def _scrub(text: str, token: str) -> str:
    return text.replace(token, "<token>") if token else text


def check_ids(new: dict[str, str], src: dict[str, str], *, allow_same_ids: bool = False) -> None:
    """`new` must name exactly the paths of `src`, each once, under ids that are not the source's own."""
    if len(set(new.values())) != len(new):
        raise IndexError_(f"{len(new) - len(set(new.values()))} paths have more than one id in the new space")
    missing, extra = set(src.values()) - set(new.values()), set(new.values()) - set(src.values())
    if missing or extra:
        raise IndexError_(f"the new space's paths differ from the source's: {len(missing)} missing, {len(extra)} extra")
    if not allow_same_ids and set(new) == set(src):
        raise IndexError_("every file id equals the source index's: the provider or the space resolved to the source's own, so this would label B's runs with site_g's ids")


def build_provider_index(src_index_root, out_index_root, *, host: str | None = None, space: str | None = None, token: str = "",
                         session=None, ids: dict[str, str] | None = None, allow_same_ids: bool = False, verify=None) -> dict:
    """Write `<out_index_root>/layout/{index.npz,ids.json,digest.json}`. `ids`: given instead of fetched (a stub or a file). `verify`: called with the output
    root (default `fullindex.load_full_index`). Returns counts."""
    src_dir, out_dir = fullindex.index_dir(Path(src_index_root)), fullindex.index_dir(Path(out_index_root))
    for f in FILES:
        if not (src_dir / f).is_file():
            raise IndexError_(f"the source index at {src_dir} has no {f}")
    digest = json.loads((src_dir / "digest.json").read_text())
    if digest.get("manifest_sha256") != fullindex.manifest_digest():
        raise IndexError_(f"the source index at {src_dir} was built from other manifests: rebuild it")
    if out_dir.exists() and any(out_dir.iterdir()):
        raise IndexError_(f"{out_dir} already holds an index: never overwritten")
    src_ids = json.loads((src_dir / "ids.json").read_text())
    if ids is None:
        if not (host and space and token):
            raise IndexError_("a provider host, a space name and a token are needed to read the ids")
        try:
            ids = fullindex.fetch_ids(host, space, token, session=session)
        except Exception as e:      # noqa: BLE001 -- whatever the REST client raised, without the token in it
            raise IndexError_(f"reading the ids from {host} failed: {type(e).__name__}: {_scrub(str(e), token)[:200]}") from None
    check_ids(ids, src_ids, allow_same_ids=allow_same_ids)
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copyfile(src_dir / "index.npz", out_dir / "index.npz")
        (out_dir / "ids.json").write_text(json.dumps(ids))
        (out_dir / "digest.json").write_text(json.dumps({**digest, "ids": len(ids)}, indent=1))
        (verify or fullindex.load_full_index)(Path(out_index_root))
    except BaseException:
        for f in FILES:
            (out_dir / f).unlink(missing_ok=True)
        raise
    return {"ids": len(ids), "files": digest.get("files"), "same_ids_as_source": set(ids) == set(src_ids), "out": str(out_dir)}


def read_token(token_file: str | None, token_env: str | None) -> str:
    if token_file:
        t = Path(token_file).read_text().strip()
    elif token_env:
        t = os.environ.get(token_env, "").strip()
    else:
        raise IndexError_("give --token-file or --token-env")
    if not t:
        raise IndexError_("the token is empty")
    return t


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m snapshot.bindex", description=__doc__.split("\n\n")[0])
    ap.add_argument("--src-index-root", required=True, type=Path, help="a root whose layout/ is the source index (main's, or ICSA_DATA)")
    ap.add_argument("--out-index-root", required=True, type=Path, help="the new root: layout/ is made under it; give Production --data-dir too (its s1z is not here)")
    ap.add_argument("--provider-host")
    ap.add_argument("--space-name")
    ap.add_argument("--token-file")
    ap.add_argument("--token-env")
    ap.add_argument("--ids-file", type=Path, help="read {file id: path} from this file instead of the provider (a stub, a rehearsal)")
    ap.add_argument("--allow-same-ids", action="store_true", help="accept ids equal to the source's (a rehearsal on a copy; never for a real provider)")
    ns = ap.parse_args(argv)
    token = ""
    try:
        ids = json.loads(ns.ids_file.read_text()) if ns.ids_file else None
        if ids is None:
            token = read_token(ns.token_file, ns.token_env)
        r = build_provider_index(ns.src_index_root, ns.out_index_root, host=ns.provider_host, space=ns.space_name, token=token, ids=ids,
                                 allow_same_ids=ns.allow_same_ids)
    except (IndexError_, OSError, ValueError) as e:
        print(f"bindex FAILED {type(e).__name__}: {_scrub(str(e), token)[:300]}", file=sys.stderr)
        return 2
    print(f"bindex ok ids={r['ids']} files={r['files']} same_ids_as_source={r['same_ids_as_source']} out={r['out']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
