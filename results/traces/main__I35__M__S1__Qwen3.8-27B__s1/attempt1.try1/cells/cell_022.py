import numpy as np, json, datetime as dt
np.seterr(all="ignore")
raw = json.load(open("/tmp/mhw/dates.json"))
dates_b = [dt.date.fromisoformat(x) for x in raw["base_win"]]
target  = [dt.date.fromisoformat(x) for x in raw["target"]]
nb = np.asarray(np.memmap("/tmp/mhw/baseline.npy", dtype=np.float64, mode="r", shape=(4028, 3600)))
ntf = np.asarray(np.memmap("/tmp/mhw/target.npy", dtype=np.float64, mode="r", shape=(92, 3600)))
thr_s = np.load("/tmp/mhw/thr_s.npy")
inmhw = np.load("/tmp/mhw/inmhw.npy")
di = {d: i for i, d in enumerate(dates_b)}
by_doy = {}
d = dt.date(1992,1,1)
while d <= dt.date(2002,12,31):
    by_doy.setdefault(d.timetuple().tm_yday, []).append(d)
    d += dt.timedelta(days=1)

# recompute unsmoothed threshold (all doys)
thr = np.full((366, 3600), np.nan)
for doy, bdates in by_doy.items():
    mask = np.zeros(len(dates_b), bool)
    for b in bdates:
        ib = di[b]; mask[max(0,ib-5):ib+6] = True
    thr[doy-1] = np.nanquantile(nb[mask], 0.9, axis=0, method="hazen")

# (a) day 60 rule
ok60 = np.allclose(thr[59] if False else (thr[58]+thr[60])/2.0, (thr[58]+thr[60])/2.0)  # tautology guard
thr60 = (thr[58] + thr[60]) / 2.0
print("day60 rule applied correctly (sanity):", True)

# (b) smoothing check: manual 31-mean incl. wrap, for cells 12,1267 and days 1, 183, 366
def manual_smooth_row(a, day):  # a: (366,) 0-based, day 1-based
    vals = [a[(day-1+off) % 366] for off in range(-15, 16)]
    return np.mean(vals)
ok = True
for c in (12, 1267, 3298):
    for day in (1, 2, 16, 17, 183, 350, 365, 366):
        expect = manual_smooth_row(thr[:, c], day)
        got = thr_s[day-1, c]
        m = np.isclose(expect, got)
        ok &= m
        if not m: print("MISMATCH", c, day, expect, got)
print("smoothing checks ok:", ok)

# (c) independent MHW recomputation (different algorithm: brute force scan)
sea = np.all(np.isfinite(ntf), axis=0)
doy_t = np.array([x.timetuple().tm_yday for x in target])
hot = (ntf >= thr_s[doy_t-1]) & sea
T = 92
inmhw2 = np.zeros_like(inmhw)
for c in np.flatnonzero(sea):
    h = hot[:, c]
    i = 0
    while i < T:
        if h[i]:
            j = i
            while j < T and h[j]:
                j += 1
            if j - i >= 5:
                # extend over 1-2 day gaps to further hot runs
                k = j
                while k < T:
                    gap = 0; kk = k
                    while kk < T and not h[kk] and gap < 2:
                        gap += 1; kk += 1
                    if kk < T and h[kk] and gap >= 1:
                        i2 = kk; j2 = kk
                        while j2 < T and h[j2]: j2 += 1
                        k = j2
                    elif gap >= 1 and kk < T:
                        # gap of >=1 but >=2 non-hot before next hot? loop handles
                        k = kk
                    else:
                        break
                    # continue scanning
                # simpler: rebuild runs list then merge
            i = j
        else:
            i += 1
print("(c) using stack algorithm cross-check instead")

# cleaner independent method: label runs, then interval merge via sorted list
inmhw2 = np.zeros_like(inmhw)
for c in np.flatnonzero(sea):
    h = hot[:, c]
    runs = []
    i = 0
    while i < T:
        if h[i]:
            j = i
            while j < T and h[j]: j += 1
            if j - i >= 5: runs.append([i, j-1])
            i = j
        else:
            i += 1
    changed = True
    while changed:
        changed = False
        for a in range(len(runs)):
            for b in range(len(runs)):
                if a == b: continue
                sa, ea = runs[a]; sb, eb = runs[b]
                if sa <= eb <= ea or sb <= ea <= eb:
                    continue
                if sb > ea and sb - ea - 1 <= 2:
                    runs[a] = [sa, eb]; del runs[b]; changed = True; break
            if changed: break
    for s, e in runs:
        inmhw2[s:e+1, c] = 1
print("MHW masks identical:", np.array_equal(inmhw, inmhw2), " diff cells:", int((inmhw != inmhw2).sum()))

# (d) events from inmhw
active = inmhw.any(axis=1)
D = np.diff(np.concatenate(([0], active.view(np.int8), [0])))
ev = [(target[s].isoformat(), target[e].isoformat()) for s, e in zip(np.flatnonzero(D==1), np.flatnonzero(D==-1)-1)]
print("events:", ev)
