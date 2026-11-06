"""stdin: `provider epoch|none` lines; argv: t_epoch out_file. Writes `provider<TAB>tar_mtime_utc<TAB>age_vs_t_s<TAB>label` (lane-snap6, 6 Nov; the lead 06:2xZ)."""
import datetime as dt, sys
ts = int(sys.argv[1]); old = {f"icsa-site_a-{n}" for n in range(14, 20)}
rows = []
for l in sys.stdin:
    if not l.strip():
        continue
    p, m = l.split()
    if m == "none":
        rows.append(f"{p}\tnone\t\ttar missing"); continue
    m = int(m)
    lab = "live store unreadable (job step limit), idle since 5 Nov 17:34Z" if p in old else "exporter last write"
    rows.append(f"{p}\t{dt.datetime.fromtimestamp(m, dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}\t{ts - m}\t{lab}")
open(sys.argv[2], "w").write("\n".join(rows) + "\n")
ages = [int(r.split("\t")[2]) for r in rows if r.split("\t")[2]]
print(f"hpc-tar-ages: {len(rows)} HPC store tars; age vs t min {min(ages)} s, max {max(ages)} s; icsa-site_a-14..19 labelled unreadable/idle ({sum(1 for r in rows if r.split(chr(9))[0] in old)} of them)")
