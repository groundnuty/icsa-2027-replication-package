#!/usr/bin/env python3
"""Write the image registry from the unpacker's records (`ociunpack.py` prints one per image) and check it against the campaign's pins.

    python3 build_images.py --images-dir <dir with sandbox.sif, sandbox.unpack.json, oneclient.sif, ...> [--pins pins.json] [--out images.json]

The `id` of an image is the OCI manifest digest of the archive, which is what Docker's containerd image store calls the image id; pins.json holds the same digest. A mismatch
with the pins is an error: this must never report a pinned id for an image that is another one.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

TAGS = {"sandbox": ["icsa-sandbox:oracle-09ecc2c0e657"], "oneclient": ["onedata/oneclient:25.0"]}
PIN_KEYS = {"sandbox": ("sandbox_image", "id"), "oneclient": ("oneclient_image", "id")}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--images-dir", required=True)
    ap.add_argument("--pins")
    ap.add_argument("--archive", help="the docker-save archive the SIFs were built from: its sha256 is recorded in the registry and so in every run record")
    ap.add_argument("--out")
    a = ap.parse_args()
    d = Path(a.images_dir)
    pins = json.loads(Path(a.pins).read_text()) if a.pins else None
    images = []
    for name, tags in TAGS.items():
        rec = json.loads((d / f"{name}.unpack.json").read_text())
        sif = d / f"{name}.sif"
        if pins:
            key, sub = PIN_KEYS[name]
            if pins[key][sub] != rec["manifest_digest"]:
                sys.exit(f"{name}: the unpacked image is {rec['manifest_digest']}, the pins say {pins[key][sub]}")
        images.append({"name": name, "id": rec["manifest_digest"], "config_digest": rec["config_digest"], "tags": tags, "sif": str(sif), "sif_sha256": sha256_file(sif),
                       "diff_ids": rec["diff_ids"], "config": rec["config"], "built_by": "hpc_sandbox/ociunpack.py + apptainer build"})
    reg = {"images": images}
    if a.archive:
        reg["archive_sha256"] = sha256_file(Path(a.archive))
        reg["archive_name"] = Path(a.archive).name
    out = Path(a.out or d / "images.json")
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(json.dumps(reg, indent=1))
    tmp.replace(out)                                   # whole file or nothing: dockers read it every call
    print(f"wrote {out}: " + ", ".join(f"{i['name']} {i['id'][:19]}" for i in images) + (" (pins checked)" if pins else " (NO pins checked)"))


if __name__ == "__main__":
    main()
