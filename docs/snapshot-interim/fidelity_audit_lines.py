"""The audit lines fault calibration's `score` needs, taken from our incremental audit store instead of a second read of site_g (lane-snap, #34; science 5 Nov 06:58Z).

    python fidelity_audit_lines.py --slot-map CONFIG/slot_map.json --windows RUNS.json --pad-s 600 --until 2026-11-05T03:35:00Z --out LINES [--since ISO] [--stores backfill,live]

`m-audit/{backfill,live}` hold site_g's file_access_audit.log lines of every slot user (93) from 4 Nov 00:33:45Z on, read incrementally and byte-exact (chunks/*.log.gz named by ledger.jsonl). Writes to --out
(one raw line per output line, in the ledger's order = the source's order) the lines of the users of the runs in --windows (a JSON list of {slot, *_utc} per run, from the root's run.json files) that fall inside
one of that user's run windows widened by --pad-s, up to --until; the same text `pull_logs` greps for (`user: <id>;`). The window filter is the one deviation from `pull_logs`: the slots' lines outside every
run window are tens of GB-lines of the main campaign's own runs on the same slot users, and `score` attributes a line by (user, run window +- margin 2 s), so a line outside every window is never read.
Prints counts only (lines read, lines kept, first and last kept timestamp, bytes). Reads the chunks of a ledger row only when the file is there; a ledger row whose chunk is missing is a hard error
(a silent hole would read as `no faulted line`)."""
from __future__ import annotations

import argparse
import bisect
import calendar
import gzip
import json
import re
import sys
from pathlib import Path

_TS = re.compile(rb"^\[(\d{4})-(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d)\.(\d{3})\]")


def ts_of(line: bytes):
    m = _TS.match(line)
    if not m:
        return None
    y, mo, d, h, mi, s, ms = map(int, m.groups())
    return calendar.timegm((y, mo, d, h, mi, s, 0, 0, 0)) + ms / 1000


def iso_epoch(x: str) -> float:
    import datetime as dt
    return dt.datetime.fromisoformat(x.replace("Z", "+00:00")).timestamp()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slot-map", required=True)
    ap.add_argument("--windows", required=True, help="JSON list: per run {slot, started_utc, run_start_utc, lease_start_utc, warm_start_utc, run_end_utc, lease_end_utc, warm_end_utc, token_valid_until_utc}")
    ap.add_argument("--pad-s", type=float, default=600.0)
    ap.add_argument("--until", required=True)
    ap.add_argument("--since", default=None)
    ap.add_argument("--root", default="/mnt/volume2/icsa-2027/m-audit")
    ap.add_argument("--stores", default="backfill,live")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    sm = json.loads(Path(a.slot_map).read_text())
    runs = json.loads(Path(a.windows).read_text())
    pad = a.pad_s
    wins: dict[str, list[tuple[float, float]]] = {}
    for r in runs:
        slot = r.get("slot")
        if not slot:
            continue
        starts = [iso_epoch(r[k]) for k in ("started_utc", "run_start_utc", "lease_start_utc", "warm_start_utc") if r.get(k)]
        ends = [iso_epoch(r[k]) for k in ("run_end_utc", "lease_end_utc", "warm_end_utc") if r.get(k)]
        if not ends and r.get("token_valid_until_utc"):          # a crashed run left no end: its widest known span runs to the token's expiry
            ends = [iso_epoch(r["token_valid_until_utc"])]
        if not starts or not ends:
            raise SystemExit(f"run {r.get('run')}: no usable window (starts {len(starts)}, ends {len(ends)})")
        wins.setdefault(sm[slot]["user"], []).append((min(starts) - pad, max(ends) + pad))
    merged: dict[str, list[tuple[float, float]]] = {}
    for u, ws in wins.items():
        out_w: list[tuple[float, float]] = []
        for a0, b0 in sorted(ws):
            if out_w and a0 <= out_w[-1][1]:
                out_w[-1] = (out_w[-1][0], max(out_w[-1][1], b0))
            else:
                out_w.append((a0, b0))
        merged[u] = out_w
    starts_of = {u: [w[0] for w in ws] for u, ws in merged.items()}
    users = sorted(merged)
    if not users or not all(re.fullmatch(r"[A-Za-z0-9]+", u) for u in users):
        raise SystemExit("slot users must be alphanumeric ids")
    pat = re.compile(rb"user: (" + b"|".join(u.encode() for u in users) + rb");")
    until = iso_epoch(a.until)
    since = iso_epoch(a.since) if a.since else None
    n_read = n_keep = nbytes = 0
    first = last = None
    tmp = Path(a.out + ".tmp")
    with open(tmp, "wb") as out:
        for store in a.stores.split(","):
            led = Path(a.root) / store / "ledger.jsonl"
            for raw in led.read_text().splitlines():
                if not raw.strip():
                    continue
                r = json.loads(raw)
                if r.get("kind") != "pull" or not r.get("n_lines") or not r.get("chunk"):
                    continue
                p = Path(a.root) / store / r["chunk"]
                if not p.is_file():
                    raise SystemExit(f"ledger row {store}#{r.get('seq')}: chunk {p} is missing (a hole would read as no faulted line)")
                with gzip.open(p, "rb") as fh:
                    for ln in fh:
                        n_read += 1
                        if not pat.search(ln):
                            continue
                        t = ts_of(ln)
                        if t is None or t > until or (since is not None and t < since):
                            continue
                        mu = pat.search(ln).group(1).decode()
                        i = bisect.bisect_right(starts_of[mu], t) - 1
                        if i < 0 or t > merged[mu][i][1]:
                            continue                                 # outside every run window of that user
                        out.write(ln if ln.endswith(b"\n") else ln + b"\n")
                        n_keep += 1
                        nbytes += len(ln)
                        first = t if first is None else first
                        last = t
    tmp.replace(a.out)
    fmt = lambda t: None if t is None else __import__("datetime").datetime.fromtimestamp(t, __import__("datetime").timezone.utc).isoformat(timespec="seconds")
    print(json.dumps({"users": len(users), "lines_read": n_read, "lines_kept": n_keep, "bytes": nbytes, "first": fmt(first), "last": fmt(last)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
