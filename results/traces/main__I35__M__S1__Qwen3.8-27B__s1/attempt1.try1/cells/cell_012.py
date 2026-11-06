import numpy as np, json, datetime as dt
np.seterr(all="ignore")

dates_b = json.load(open("/tmp/mhw/dates.json"))["base_win"]
target  = json.load(open("/tmp/mhw/dates.json"))["target"]
nb = np.asarray(np.memmap("/tmp/mhw/baseline.npy", dtype=np.float64, mode="r", shape=(4028, 3600)))
ntf = np.asarray(np.memmap("/tmp/mhw/target.npy",   dtype=np.float64, mode="r", shape=(92, 3600)))

date_to_idx = {d: i for i, d in enumerate(dates_b)}
base_start, base_end = "1992-01-01", "2002-12-31"

# group baseline dates by day-of-year
by_doy = {}
d = dt.date(1992,1,1)
while d <= dt.date(2002,12,31):
    by_doy.setdefault(d.timetuple().tm_yday, []).append(d)
    d += dt.timedelta(days=1)

thr = np.full((366, 3600), np.nan)
clim = np.full((366, 3600), np.nan)
pool_sizes = {}
for doy, bdates in by_doy.items():
    mask = np.zeros(len(dates_b), dtype=bool)
    for b in bdates:
        ib = date_to_idx[b]
        mask[max(0, ib-5): min(len(dates_b), ib+6)] = True
    rows = np.flatnonzero(mask)
    pool_sizes[doy] = len(rows)
    pool = nb[rows]
    thr[doy-1]  = np.nanquantile(pool, 0.9, axis=0, method="hazen")
    clim[doy-1] = np.nanmean(pool, axis=0)

print("day60 in by_doy:", 60 in by_doy)
print("doy 366 pool size:", pool_sizes[366], " doy 365:", pool_sizes[365], " doy 1:", pool_sizes[1])

# day 60 = mean of 59 and 61 (0-based idx 58,60 -> idx 59)
thr[59]  = (thr[58] + thr[60]) / 2.0
clim[59] = (clim[58] + clim[60]) / 2.0

# 31-day centred moving mean with wrap over 366
def smooth366(a):
    out = np.zeros_like(a)
    idx366 = np.arange(366)
    for off in range(-15, 16):
        out += np.take(a, (idx366 + off) % 366, axis=0)
    return out / 31.0

thr_s = smooth366(thr)
clim_s = smooth366(clim)
print("thr_s NaN cells:", int(np.isnan(thr_s).any(axis=0).sum()), " clim_s NaN cells:", int(np.isnan(clim_s).any(axis=0).sum()))
np.save("/tmp/mhw/thr_s.npy", thr_s)
np.save("/tmp/mhw/clim_s.npy", clim_s)
print("threshold/climatology done")
