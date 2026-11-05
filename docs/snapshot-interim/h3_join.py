"""The platform rows of every audit store, joined into the ONE file `mainaudit measure --platform` takes (lane-snap, #34).

    python h3_join.py --providers M/providers.json --store site_g=DIR --store site_u=DIR ... --out platform_rows.jsonl

Each extract store (`mainaudit extract --store DIR`) writes DIR/platform_rows.jsonl: one row per run that has a finished attempt in ITS mirror ({run, block, platform_record}).
The merged store says who owns each run (`bmerge`'s providers.json: store run key `<block>__<run>` -> provider name, main = "site_g"; first started attempt wins). A run's row is taken
from its OWNER's store only, so a run both main and a B provider reached carries the winner's record, never two (the measure refuses a duplicate key). Rows of a store for runs
that store does not own are dropped and counted. Nothing is invented: a run whose owner has no row stays without one, and the measure counts it (`no_platform_row`).
Prints counts only (rows kept and dropped per store). This is glue between two frozen tools, new code: it changes neither.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--providers", required=True, type=Path)
    ap.add_argument("--store", action="append", default=[], metavar="NAME=DIR")
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args(argv)
    spec = json.loads(a.providers.read_text())
    if spec.get("format") != "icsa-bmerge-providers-v1":
        print(f"h3_join: {a.providers} is not a bmerge providers file", file=sys.stderr)
        return 2
    owner: dict[str, str] = spec["providers"]
    kept: dict[tuple[str, str], str] = {}
    counts: dict[str, dict] = {}
    for spec_s in a.store:
        name, _, d = spec_s.partition("=")
        p = Path(d) / "platform_rows.jsonl"
        c = counts[name] = {"rows": 0, "kept": 0, "not_owner": 0, "not_in_merged_store": 0}
        if not p.is_file():
            c["missing_file"] = 1
            continue
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            c["rows"] += 1
            o = owner.get(f"{row['block']}__{row['run']}")
            if o is None:
                c["not_in_merged_store"] += 1
            elif o != name:
                c["not_owner"] += 1
            else:
                k = (row["block"], row["run"])
                if k in kept:
                    print(f"h3_join: two stores both own {k[0]} / one run: refused", file=sys.stderr)
                    return 3
                kept[k] = line
                c["kept"] += 1
    a.out.parent.mkdir(parents=True, exist_ok=True)
    tmp = a.out.with_name(a.out.name + ".tmp")
    tmp.write_text("".join(kept[k] + "\n" for k in sorted(kept)))
    tmp.replace(a.out)
    print("h3_join rows=%d " % len(kept) + " ".join(f"{n}:kept={c['kept']}/rows={c['rows']}" + (f",not_owner={c['not_owner']}" if c["not_owner"] else "")
                                                   + (",MISSING_FILE" if c.get("missing_file") else "") for n, c in counts.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
