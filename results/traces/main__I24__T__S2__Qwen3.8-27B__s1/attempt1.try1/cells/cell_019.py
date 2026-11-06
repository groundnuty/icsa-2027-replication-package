import numpy as np, xarray as xr

sub = xr.open_dataset("/tmp/mhw/subset.nc")
sst = sub.analysed_sst.values
ts = sub.time.values.astype("datetime64[D]")
o = (ts - ts.astype("datetime64[Y]")).astype("timedelta64[D]").astype(np.int64) + 1
year = ts.astype("datetime64[Y]").astype(np.int64) + 1970
is_leap = (year % 4 == 0) & ((year % 100 != 0) | (year % 400 == 0))
doy = o + np.where(~is_leap & (o > 59), 1, 0)

thr_s = np.load("/tmp/mhw/thr_s.npy")
mask  = np.load("/tmp/mhw/mask.npy")
sea   = np.load("/tmp/mhw/sea.npy")

T0 = 4028
tt = sst[T0:]; tt_times = ts[T0:]; doys_t = doy[T0:]
hot = tt >= thr_s[doys_t - 1]

def max_runs(h):
    padded = np.concatenate(([False], h, [False]))
    dd = np.diff(padded.astype(np.int8))
    s = np.where(dd == 1)[0]; e = np.where(dd == -1)[0] - 1
    return list(zip(s, e))

errors = 0
for i in range(60):
    for j in range(60):
        if not sea[i, j]:
            if mask[:, i, j].any():
                errors += 1; print("non-sea cell has mask", i, j)
            continue
        h = hot[:, i, j]
        intervals = []
        m = mask[:, i, j].astype(bool)
        padded = np.concatenate(([False], m, [False]))
        dd = np.diff(padded.astype(np.int8))
        s = np.where(dd == 1)[0]; e = np.where(dd == -1)[0] - 1
        intervals = list(zip(s, e))
        allruns = max_runs(h)
        runs5 = [r for r in allruns if r[1] - r[0] + 1 >= 5]
        # A2b: every >=5 run inside some interval
        for (rs, re) in runs5:
            if not any(s2 <= rs and re <= e2 for (s2, e2) in intervals):
                errors += 1; print("run not covered", i, j, rs, re)
        for (s2, e2) in intervals:
            if s2 > e2: continue
            # A1: endpoints hot
            if not h[s2] or not h[e2]:
                errors += 1; print("endpoint not hot", i, j, s2, e2)
            # interior maximal hot runs
            inner = [(rs, min(re, e2)) for (rs, re) in allruns if rs >= s2 and re <= e2]
            inner = [(rs, re) for (rs, re) in inner if rs >= s2 and re <= e2 and (rs, re) in allruns]
            # take runs fully inside
            inner = [(rs, re) for (rs, re) in allruns if s2 <= rs and re <= e2]
            for k, (rs, re) in enumerate(inner):
                ln = re - rs + 1
                if ln >= 5:
                    continue
                # must be sandwiched with gaps <=2 on both sides
                prev = inner[k-1][1] if k > 0 else None
                nxt  = inner[k+1][0] if k < len(inner)-1 else None
                if prev is None or nxt is None or (rs - prev - 1) > 2 or (nxt - re - 1) > 2:
                    errors += 1; print("bad short run", i, j, rs, re, inner)
            # A2c: adjacent interior runs gap <= 2
            for k in range(len(inner)-1):
                if inner[k+1][0] - inner[k][1] - 1 > 2:
                    errors += 1; print("gap>2 inside interval", i, j, inner)
        # A2d: consecutive intervals gap >= 3
        for k in range(len(intervals)-1):
            if intervals[k+1][0] - intervals[k][1] - 1 < 3:
                errors += 1; print("intervals too close", i, j, intervals)
        # no mask days outside intervals (by construction) and no gaps inside
print("property check errors:", errors)
assert errors == 0

# independent regional event derivation (different run-finding: cumsum trick)
active = mask.any(axis=2).any(axis=1)
lab = np.cumsum(active)
events2 = []
for v in np.unique(lab[active]):
    days = np.where(lab == v)[0]
    events2.append((days.min(), days.max()))
# verify maximality: days between consecutive events are inactive
ev_ok = all(not active[events2[k][1]+1:events2[k+1][0]].any() for k in range(len(events2)-1))
print("events (independent):", [(str(tt_times[a].astype('datetime64[D]')), str(tt_times[b].astype('datetime64[D]'))) for a, b in events2], "maximal:", ev_ok)

# per-day active cell counts during/around event
for t in range(0, 92, 4):
    print(str(tt_times[t].astype('datetime64[D]')), "active cells:", int(mask[t].sum()))
print("DONE")
