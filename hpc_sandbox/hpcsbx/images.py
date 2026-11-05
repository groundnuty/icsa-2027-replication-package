"""The image registry: which SIF stands for which Docker reference, and what the image's own configuration says.

`build_images.py` writes $HPCSBX_IMAGES (default $HPCSBX_HOME/images/images.json) from the unpacker's records. A SIF built from an unpacked root filesystem carries none of the
Docker image's configuration, so the Env, WorkingDir and User of the image's config are kept here and applied on every run and exec, as Docker applies them.
"""
from __future__ import annotations

import os
from pathlib import Path

from .common import HOME, ShimError, read_json, write_json


def registry_path() -> Path:
    return Path(os.environ.get("HPCSBX_IMAGES") or HOME / "images" / "images.json")


def load() -> dict:
    reg = read_json(registry_path())
    if not reg:
        raise ShimError(f"image registry {registry_path()} is missing or unreadable (run build_images.py)")
    return reg


def aliases_path() -> Path:
    return HOME / "images" / "aliases.json"


def resolve(ref: str) -> dict:
    """The image a reference names (a tag, `host-3.invalid/library/<tag>`, the id `sha256:...` or the id without its prefix, or a tag that `docker build` was told to alias), or the
    daemon's words."""
    alias = (read_json(aliases_path(), {}) or {})
    for img in load()["images"]:
        names = set(img["tags"]) | {img["id"], img["id"].split(":", 1)[1]} | {"host-3.invalid/library/" + t for t in img["tags"]} | {"host-3.invalid/" + t for t in img["tags"]}
        names |= {t for t, target in alias.items() if target == img["name"]}
        if ref in names:
            return img
    raise ShimError(f"No such image: {ref}")


def sif_path(img: dict) -> str:
    """The node-local copy when setup_node.sh made one (page-cached RAM, no Lustre round trip per container start), else the one on scratch."""
    local = HOME / "images" / Path(img["sif"]).name
    return str(local if local.exists() else img["sif"])


def env_list(img: dict) -> dict:
    out = {}
    for kv in img.get("config", {}).get("Env") or []:
        k, _, v = kv.partition("=")
        out[k] = v
    return out


def alias(tag: str, name: str) -> dict:
    """Make `tag` another name of the registered image `name` (what a `docker build -t tag` is answered with when HPCSBX_BUILD_AS names an image: nothing is built here)."""
    img = next((i for i in load()["images"] if i["name"] == name), None)
    if img is None:
        raise ShimError(f"HPCSBX_BUILD_AS={name!r} names no registered image")
    a = read_json(aliases_path(), {}) or {}
    a[tag] = name
    write_json(aliases_path(), a)
    return img
