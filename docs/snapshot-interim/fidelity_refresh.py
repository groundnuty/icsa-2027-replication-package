"""Bring fault calibration's captures (audit.log, traefik.jsonl) in a COPY of its root up to date, in `calibrate`'s own format (lane-snap, #34; science 5 Nov 06:58Z).

    python fidelity_refresh.py --dir CAPTURE_DIR --name audit.log --new LINES --pulled-utc ISO [--files a,b] [--mark-gap-to ISO]
    python fidelity_refresh.py --dir CAPTURE_DIR --check

CAPTURE_DIR holds the root's capture files (audit.log, traefik.jsonl, PULLS.jsonl, pulls/): never the live root. `--new` is the text of the lines to add. The call is `calibrate._store_capture` itself,
with `lines` = the source as the LAST pull read it (pulls/<name>.<sha12>) + the new lines, so nothing counts as gone (n_gone stays 0: no false capture gap) and PULLS.jsonl, pulls/ and the capture
grow exactly as a `pull` would have made them. `--pulled-utc` is when the lines are complete to: a line the source wrote later may be missing, and `score` allows for it.
`--mark-gap-to ISO`: the span between the last pull and ISO was NOT read (our incremental store begins at ISO): a row with n_gone=1 and pulled_utc ISO is written first (the same sha as the last pull, no
new line), so `capture_gaps` reports (last pull, ISO) as a span where lines may be gone unseen: a run inside it is `not observed` on the audit record, never `unfaulted`.
`--check` prints, per capture, when it last read its source (the same number `score`'s coverage check reads: `calibrate.capture_times`)."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from icsa.faults import calibrate as C
from icsa.faults.records.base import Record


def last_pull_lines(d: Path, name: str) -> list[str]:
    rows = [json.loads(x) for x in (d / "PULLS.jsonl").read_text().splitlines() if x.strip()]
    last = next((r for r in reversed(rows) if r["name"] == name), None)
    if last is None:
        raise SystemExit(f"{name}: no pull in {d}/PULLS.jsonl")
    return (d / "pulls" / f"{name}.{last['sha256'][:12]}").read_text().splitlines()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--name", choices=["audit.log", "traefik.jsonl"])
    ap.add_argument("--new")
    ap.add_argument("--pulled-utc")
    ap.add_argument("--files", default="")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--mark-gap-to")
    a = ap.parse_args(argv)
    d = Path(a.dir)
    if a.check:
        got = C.capture_times(d)
        names = {Record.AUDIT: "audit.log", Record.TRAEFIK: "traefik.jsonl"}
        print(json.dumps({names[r]: dt.datetime.fromtimestamp(t, dt.timezone.utc).isoformat(timespec="milliseconds") for r, t in got.items()}))
        return 0
    if not (a.name and a.new and a.pulled_utc):
        raise SystemExit("--name, --new and --pulled-utc are required")
    pulled = dt.datetime.fromisoformat(a.pulled_utc.replace("Z", "+00:00")).astimezone(dt.timezone.utc).isoformat(timespec="milliseconds")
    if a.mark_gap_to:
        gap_end = dt.datetime.fromisoformat(a.mark_gap_to.replace("Z", "+00:00")).astimezone(dt.timezone.utc).isoformat(timespec="milliseconds")
        rows = [json.loads(x) for x in (d / "PULLS.jsonl").read_text().splitlines() if x.strip()]
        last = [r for r in rows if r["name"] == a.name][-1]
        if gap_end <= last["pulled_utc"]:
            raise SystemExit(f"--mark-gap-to {gap_end} is not after the last pull {last['pulled_utc']}")
        with (d / "PULLS.jsonl").open("a") as fh:
            fh.write(json.dumps({"name": a.name, "sha256": last["sha256"], "n_lines": last["n_lines"], "n_new": 0, "n_gone": 1, "pulled_utc": gap_end,
                                 "origin": "gap: not read (the incremental store begins here)"}) + "\n")
    prev = last_pull_lines(d, a.name)
    new = Path(a.new).read_text().splitlines()
    if a.name == "traefik.jsonl":
        new = [x for x in new if x.startswith("{")]          # pull_logs keeps the JSON lines only
    C._store_capture(d, a.name, prev + new, pulled, files=[f for f in a.files.split(",") if f] or None)
    rows = [json.loads(x) for x in (d / "PULLS.jsonl").read_text().splitlines() if x.strip()]
    last = [r for r in rows if r["name"] == a.name][-1]
    print(json.dumps({k: last[k] for k in ("n_lines", "n_new", "n_gone", "pulled_utc") if k in last}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
