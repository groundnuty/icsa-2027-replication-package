#!/usr/bin/env python3
"""Unpack one image of a `docker save` archive (an OCI layout) into a root filesystem directory, as an ordinary user, with Python 3.9+ and the standard library only.

Why this exists: site_a's Apptainer 1.5.4 cannot read the campaign's image archive. Its `oci:` reader fails on the layer that carries `etc/shadow` (owner root:42, mode 0640:
"error writing layer: expected blob size 3407, but only wrote ...") and `skopeo copy` into a fresh layout does not help, because the failing step is Apptainer's own unpack as a
non-root user. A user cannot be root, so this keeps no ownership (every file is the unpacking user's, which is also who runs the container) and skips device nodes (the runtime
supplies /dev). It does what an image's layers mean: layers in order, `.wh.<name>` removes <name>, `.wh..wh..opq` empties the directory below it, hard links, symlinks.

    python3 ociunpack.py <layout-dir> <ref-name or manifest digest> <rootfs-dir>

It prints a JSON record of what it unpacked: the manifest digest (which is what Docker calls the image id under its containerd store: `pins.json` pins it), the config digest
and the config's diff ids, so the unpacked tree can be tied to the pinned image. It refuses a layer whose uncompressed sha256 differs from its diff id.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import stat
import sys
import tarfile


def blob(layout: str, digest: str) -> str:
    algo, _, hexd = digest.partition(":")
    return os.path.join(layout, "blobs", algo, hexd)


def pick_manifest(layout: str, want: str) -> dict:
    idx = json.load(open(os.path.join(layout, "index.json")))
    for m in idx["manifests"]:
        if m["digest"] == want or m.get("annotations", {}).get("org.opencontainers.image.ref.name") == want:
            return m
    raise SystemExit(f"no image {want!r} in {layout}: " + ", ".join(m.get("annotations", {}).get("org.opencontainers.image.ref.name", m["digest"]) for m in idx["manifests"]))


def _clear_dir(path: str) -> None:
    for name in os.listdir(path):
        _remove(os.path.join(path, name))


def _remove(path: str) -> None:
    if os.path.islink(path) or not os.path.isdir(path):
        os.unlink(path)
        return
    _clear_dir(path)
    os.rmdir(path)


def norm(name: str) -> str:
    """A member name relative to the root: leading `./` pairs and slashes only. (`lstrip("./")` would also eat the dots of `.env` and of `.wh.<name>`.)"""
    while name.startswith("./"):
        name = name[2:]
    return "" if name == "." else name.lstrip("/")


def resolve_in_root(root: str, parts: list) -> str:
    """The real path of root/<parts> as the image itself would resolve it: a symlink on the way is followed with an absolute target taken from the image's root (`/run`, not the host's),
    and `..` never leaves it. A layer that writes through `d -> /tmp` therefore writes to <root>/tmp."""
    comps = [x for x in parts if x]
    cur: list = []
    i = hops = 0
    while i < len(comps):
        c = comps[i]
        if c == ".":
            i += 1
            continue
        if c == "..":
            cur = cur[:-1]
            i += 1
            continue
        here = os.path.join(root, *cur, c)
        if os.path.islink(here):
            hops += 1
            if hops > 40:
                raise SystemExit(f"too many symbolic links resolving {'/'.join(parts)}")
            target = os.readlink(here)
            if target.startswith("/"):
                cur = []
            comps = [x for x in target.split("/") if x] + comps[i + 1:]
            i = 0
            continue
        cur.append(c)
        i += 1
    return os.path.join(root, *cur)


class Hasher:
    """A file object that hashes what is read through it (the layer's uncompressed bytes, for the diff id)."""

    def __init__(self, f):
        self.f, self.h = f, hashlib.sha256()

    def read(self, n=-1):
        d = self.f.read(n)
        self.h.update(d)
        return d


def _open_stream(path: str):
    raw = open(path, "rb")
    head = raw.read(2)
    raw.seek(0)
    return gzip.GzipFile(fileobj=raw) if head == b"\x1f\x8b" else raw


def opaque_dirs(path: str) -> list:
    """The directories a layer marks opaque, found first: an opaque marker hides what the LOWER layers put in that directory, whatever the order of entries in this layer, so it must
    not delete what this same layer adds before the marker."""
    out = []
    with tarfile.open(fileobj=_open_stream(path), mode="r|") as tf:
        for m in tf:
            parts = norm(m.name).split("/")
            if parts[-1] == ".wh..wh..opq":
                out.append(parts[:-1])
    return out


def unpack_layer(path: str, root: str, diff_id: str) -> dict:
    n = {"files": 0, "dirs": 0, "links": 0, "hardlinks": 0, "whiteouts": 0, "skipped_special": 0}
    for parts in opaque_dirs(path):
        d = resolve_in_root(root, parts)
        if os.path.isdir(d) and not os.path.islink(d):
            _clear_dir(d)
        n["whiteouts"] += 1
    hs = Hasher(_open_stream(path))
    deferred_dirs: list = []
    with tarfile.open(fileobj=hs, mode="r|") as tf:
        for m in tf:
            name = norm(m.name)
            if not name:
                continue
            parts = name.split("/")
            if any(p == ".." for p in parts):
                raise SystemExit(f"unsafe path in layer: {m.name!r}")
            base = parts[-1]
            parent = resolve_in_root(root, parts[:-1])
            dest = os.path.join(parent, base)
            if base == ".wh..wh..opq":
                continue                                   # done before the layer was unpacked
            if base.startswith(".wh."):
                target = os.path.join(parent, base[4:])
                if os.path.lexists(target):
                    _remove(target)
                n["whiteouts"] += 1
                continue
            os.makedirs(parent, exist_ok=True)
            if os.path.lexists(dest) and not (m.isdir() and os.path.isdir(dest) and not os.path.islink(dest)):
                _remove(dest)
            if m.isdir():
                os.makedirs(dest, exist_ok=True)
                os.chmod(dest, 0o755)                      # writable while the layer is unpacked: the real mode is set at the end of the layer
                deferred_dirs.append((dest, m.mode & 0o7777))
                n["dirs"] += 1
            elif m.isreg():
                with open(dest, "wb") as out:
                    src = tf.extractfile(m)
                    while True:
                        chunk = src.read(1 << 20)
                        if not chunk:
                            break
                        out.write(chunk)
                os.chmod(dest, (m.mode & 0o7777 & ~0o6000) | 0o600)       # owner can always read and write what the image said another owner could; no setuid or setgid bits
                n["files"] += 1
            elif m.issym():
                os.symlink(m.linkname, dest)
                n["links"] += 1
            elif m.islnk():
                src = resolve_in_root(root, norm(m.linkname).split("/"))
                os.link(src, dest)
                n["hardlinks"] += 1
            else:
                n["skipped_special"] += 1                  # device nodes, fifos
    while True:                                            # the rest of the stream is padding: it belongs to the layer's hash
        if not hs.read(1 << 20):
            break
    got = "sha256:" + hs.h.hexdigest()
    if got != diff_id:
        raise SystemExit(f"layer {path}: its uncompressed sha256 is {got}, the config says {diff_id}")
    for d, mode in reversed(deferred_dirs):
        os.chmod(d, mode | 0o700)
    return n


def main(layout: str, want: str, root: str) -> None:
    m = pick_manifest(layout, want)
    man = json.load(open(blob(layout, m["digest"])))
    cfg = json.load(open(blob(layout, man["config"]["digest"])))
    diffs = cfg["rootfs"]["diff_ids"]
    if len(diffs) != len(man["layers"]):
        raise SystemExit("the config and the manifest disagree on the layer count")
    os.makedirs(root, exist_ok=True)
    if os.listdir(root):
        raise SystemExit(f"{root} is not empty")
    counts = [unpack_layer(blob(layout, l["digest"]), root, d) for l, d in zip(man["layers"], diffs)]
    print(json.dumps({"manifest_digest": m["digest"], "config_digest": man["config"]["digest"], "diff_ids": diffs, "layers": counts, "config": cfg.get("config", {}),
                      "os": cfg.get("os"), "architecture": cfg.get("architecture")}, indent=1))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
