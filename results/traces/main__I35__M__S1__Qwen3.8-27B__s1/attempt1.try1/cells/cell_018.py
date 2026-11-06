import numpy as np, json, datetime as dt
np.seterr(all="ignore")
raw = json.load(open("/tmp/mhw/dates.json"))
nb = np.asarray(np.memmap("/tmp/mhw/baseline.npy", dtype=np.float64, mode="r", shape=(4028, 3600)))
ntf = np.asarray(np.memmap("/tmp/mhw/target.npy", dtype=np.float64, mode="r", shape=(92, 3600)))
sea = np.all(np.isfinite(ntf), axis=0)
cells = [int(x) for x in np.flatnonzero(sea)[::1000]][:4]
print("test cells (sea):", cells)

dates_b = [dt.date.fromisoformat(x) for x in raw["base_win"]]
di = {d: i for i, d in enumerate(dates_b)}

def hazen_quantile_1d(vals, p=0.9):
    v = np.sort(vals); n = len(v)
    h = (n + 1) * p
    lo = min(max(int(np.floor(h)), 1), n); hi = min(max(int(np.ceil(h)), 1), n)
    if lo == hi: return float(v[lo-1])
    return float((h - lo) * v[hi-1] + (hi - h) * v[lo-1])

by_doy = {}
d = dt.date(1992,1,1)
while d <= dt.date(2002,12,31):
    by_doy.setdefault(d.timetuple().tm_yday, []).append(d)
    d += dt.timedelta(days=1)

all_ok = True
for c in cells:
    for doy in (61, 183, 300, 366):
        # slow explicit
        vals = []
        for b in by_doy[doy]:
            for off in range(-5, 6):
                i = di.get(b + dt.timedelta(days=off))
                if i is not None and np.isfinite(nb[i, c]):
                    vals.append(nb[i, c])
        q_slow, m_slow = hazen_quantile_1d(vals), np.mean(vals)
        # vectorized
        mask = np.zeros(len(dates_b), bool)
        for b in by_doy[doy]:
            ib = di[b]; mask[max(0,ib-5):ib+6] = True
        q = np.nanquantile(nb[mask, c], 0.9, method="hazen"); m = np.nanmean(nb[mask, c])
        ok = np.isclose(q, q_slow) and np.isclose(m, m_slow) and len(vals) == int(mask.sum())
        all_ok &= ok
        print(f"cell {c} doy {doy}: n={len(vals)} q_vec={q:.6f} q_slow={q_slow:.6f} m_vec={m:.6f} m_slow={m_slow:.6f} match={ok}")
print("ALL OK:", all_ok)
