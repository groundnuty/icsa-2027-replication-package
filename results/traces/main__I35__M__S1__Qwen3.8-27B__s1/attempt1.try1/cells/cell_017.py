import numpy as np, json, datetime as dt, h5py
np.seterr(all="ignore")
BASE = "/data/icsa2027_data_20261101T090944Z/s1z"
raw = json.load(open("/tmp/mhw/dates.json"))
nb = np.asarray(np.memmap("/tmp/mhw/baseline.npy", dtype=np.float64, mode="r", shape=(4028, 3600)))
dates_b = [dt.date.fromisoformat(x) for x in raw["base_win"]]
di = {d: i for i, d in enumerate(dates_b)}
thr_s = np.load("/tmp/mhw/thr_s.npy")

# --- slow explicit recomputation for chosen cells and days ---
def hazen_quantile_1d(vals, p=0.9):
    v = np.sort(vals)
    n = len(v)
    h = (n + 1) * p
    lo = int(np.floor(h)); hi = int(np.ceil(h))
    if lo < 1: lo = 1
    if hi > n: hi = n
    if lo == hi: return float(v[lo-1])
    return float((h - lo) * v[hi-1] + (hi - h) * v[lo-1])

def pool_for_doy(doy, cell):
    vals = []
    d = dt.date(1992,1,1)
    while d <= dt.date(2002,12,31):
        if d.timetuple().tm_yday == doy:
            for off in range(-5, 6):
                t = d + dt.timedelta(days=off)
                i = di.get(t)
                if i is not None:
                    v = nb[i, cell]
                    if np.isfinite(v):
                        vals.append(v)
        d += dt.timedelta(days=1)
    return np.array(vals)

cells = [7, 1234, 3301]
checks = []
for c in cells:
    for doy in (61, 183, 300, 366):
        vals = pool_for_doy(doy, c)
        q_slow = hazen_quantile_1d(vals)
        m_slow = vals.mean()
        checks.append((c, doy, q_slow, m_slow, len(vals)))
        # compare against unsmoothed array? we only saved smoothed; recompute unsmoothed here for this doy/cell
print("slow pools (cell, doy, hazen90, mean, n):")
for r in checks: print(r)

# compare with a fresh vectorized unsmoothed computation restricted to these doys
by_doy = {}
d = dt.date(1992,1,1)
while d <= dt.date(2002,12,31):
    by_doy.setdefault(d.timetuple().tm_yday, []).append(d)
    d += dt.timedelta(days=1)
for c in cells:
    for doy in (61, 183, 300, 366):
        mask = np.zeros(len(dates_b), bool)
        for b in by_doy[doy]:
            ib = di[b]; mask[ib-5:ib+6] = True
        pool = nb[mask, c]
        q = np.nanquantile(pool, 0.9, method="hazen")
        m = np.nanmean(pool)
        slow = [r for r in checks if r[0]==c and r[1]==doy][0]
        ok = np.isclose(q, slow[2]) and np.isclose(m, slow[3])
        print(f"cell {c} doy {doy}: vectorized q={q:.6f} m={m:.6f} slow q={slow[2]:.6f} m={slow[3]:.6f} match={ok}")
