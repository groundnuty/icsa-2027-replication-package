script = r'''
import numpy as np, json, warnings
from datetime import date, timedelta
import xarray as xr

warnings.filterwarnings("ignore")

z = np.load('/work/cache/data.npz')
A_base = z['A_base'].astype(np.float64)   # (4028,60,60)
A_tgt  = z['A_tgt'].astype(np.float64)    # (92,60,60)
lat = z['lat']; lon = z['lon']
dates = json.load(open('/work/cache/dates.json'))
base_dates = [date.fromisoformat(s) for s in dates['base']]
tgt_dates  = [date.fromisoformat(s) for s in dates['tgt']]
assert base_dates[0] == date(1991,12,27) and base_dates[-1] == date(2003,1,5)
assert tgt_dates[0] == date(2007,6,1) and tgt_dates[-1] == date(2007,8,31)

# ---------- day-of-year mapping (leap-year month/day calendar, doy 1..366) ----------
cum = [31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335, 366]
def doy_of(d): return cum[d.month-1] + d.day
def md_of(doy):  # inverse: doy -> (month, day)
    for m in range(1, 13):
        lo = cum[m-1] + 1
        hi = cum[m]
        if lo <= doy <= hi: return (m, doy - cum[m-1])
    raise ValueError(doy)

doy_base = np.array([doy_of(d) for d in base_dates])   # (4028,)
doy_tgt  = np.array([doy_of(d) for d in tgt_dates])    # (92,)
print("target doy range:", doy_tgt.min(), doy_tgt.max())

# ---------- sea cells: finite on every target day ----------
sea = np.all(np.isfinite(A_tgt), axis=0)               # (60,60)
print("sea cells:", int(sea.sum()), "of", sea.size)

# ---------- pools per day of year ----------
# pool(d) = { t in base_dates : exists b in baseline(1992-01-01..2002-12-31) with doy(b)=d and |t-b|<=5 days }
base_idx = {d: i for i, d in enumerate(base_dates)}
pool_idx = {}
for d in range(1, 367):
    if d == 60: continue
    m, day = md_of(d)
    idx = set()
    for y in range(1992, 2003):
        b = date(y, m, day)
        for off in range(-5, 6):
            t = b + timedelta(days=off)
            if t in base_idx: idx.add(base_idx[t])
    pool_idx[d] = np.array(sorted(idx), dtype=np.int64)
print("pool size doy1:", len(pool_idx[1]), "doy61:", len(pool_idx[61]), "doy200:", len(pool_idx[200]), "doy366:", len(pool_idx[366]))
print("pool doy1 dates:", [base_dates[i].isoformat() for i in pool_idx[1][:6]], "...", [base_dates[i].isoformat() for i in pool_idx[1][-6:]])

# ---------- threshold (hazen 90th pct) & climatology (mean), per cell ----------
C = (60, 60)
thr  = np.full((366,) + C, np.nan)
clim = np.full((366,) + C, np.nan)
for d in range(1, 367):
    if d == 60: continue
    X = A_base[pool_idx[d]]                       # (k,60,60)
    thr[d-1]  = np.nanquantile(X, 0.9, method="hazen", axis=0)
    clim[d-1] = np.nanmean(X, axis=0)
# day 60 = mean of 59 and 61
thr[59]  = 0.5 * (thr[58] + thr[60])
clim[59] = 0.5 * (clim[58] + clim[60])

nan_thr_target = np.isnan(thr[doy_tgt-1]).any(axis=0)
print("cells with NaN thr in target doy:", int(nan_thr_target.sum()))
print("thr sample (doy 196=15 Jul) finite-cell min/med/max:",
      np.nanmin(thr[195]), np.nanmedian(thr[195][sea]), np.nanmax(thr[195]))

# ---------- 31-day centred wrap-around moving mean ----------
def smooth31(a):  # a: (366, ...)
    out = np.zeros_like(a)
    for j in range(-15, 16):
        out += np.roll(a, j, axis=0)
    return out / 31.0
thr_s  = smooth31(thr)
clim_s = smooth31(clim)
print("thr smoothed finite all target doy:", bool(np.isfinite(thr_s[doy_tgt-1]).all()))

# ---------- hot days ----------
hot = A_tgt >= thr_s[doy_tgt-1][None, :, :]        # (92,60,60); NaN -> False

# ---------- per-cell MHW: runs >=5, merge gaps <=2 (vectorised) ----------
T, = (92,)
H = hot.reshape(T, -1)                             # (92, 3600)
ar = np.arange(T)
# run length of maximal hot run containing i (0 if non-hot)
s = np.zeros((T, H.shape[1]))
s[0] = H[0]
for i in range(1, T):
    s[i] = np.where(H[i], s[i-1] + 1.0, 0.0)
r = np.zeros_like(s)
r[-1] = H[-1]
for i in range(T-2, -1, -1):
    r[i] = np.where(H[i], r[i+1] + 1.0, 0.0)
runlen = np.where(H > 0.5, s + r - 1.0, 0.0)
g = H > 0.5                                         # in a run of >=5: g = hot & runlen>=5
g = (runlen >= 5.0) & (H > 0.5)
# distances to nearest g day before / after
big = 10**9
Lmax = np.maximum.accumulate(np.where(g, ar[:, None], -big), axis=0)
L5 = ar[:, None] - Lmax
Rmin = np.minimum.accumulate(np.where(g, ar[:, None], big), axis=0)
R5 = Rmin - ar[:, None]
m = g | (L5 + R5 <= 3)                              # merged membership
m = m & (L5 + R5 <= 3 | g)
mhw = m.reshape(92, 60, 60)

# ---------- naive per-cell implementation for cross-check ----------
def cell_mhw(h):
    n = len(h); runs = []; i = 0
    while i < n:
        if h[i]:
            j = i
            while j + 1 < n and h[j+1]: j += 1
            runs.append((i, j)); i = j + 1
        else: i += 1
    runs = [(a, b) for a, b in runs if b - a + 1 >= 5]
    merged = []
    for a, b in runs:
        if merged and a - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))
    out = np.zeros(n, dtype=bool)
    for a, b in merged: out[a:b+1] = True
    return out

flat = H.T  # (3600, 92)
ok = True
for c in range(3600):
    if not np.array_equal(cell_mhw(flat[c]), mhw.reshape(92, 3600)[:, c]):
        ok = False; print("MISMATCH at cell", c); break
print("vectorised == naive:", ok)
assert ok

# ---------- regional events ----------
active = mhw.reshape(92, -1).any(axis=1)
events = []
i = 0
while i < 92:
    if active[i]:
        j = i
        while j + 1 < 92 and active[j+1]: j += 1
        events.append((tgt_dates[i], tgt_dates[j]))
        i = j + 1
    else:
        i += 1
print("regional events:", [(e[0].isoformat(), e[1].isoformat()) for e in events])

# ---------- outputs ----------
import os
os.makedirs('/work/output', exist_ok=True)
time_iso = [d.isoformat() for d in tgt_dates]
mhw_var = mhw.astype(np.uint8)
da = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mhw_var)},
    coords={"time": np.array(time_iso, dtype="datetime64[ns]"),
            "lat": ("lat", lat.astype(np.float32)),
            "lon": ("lon", lon.astype(np.float32))},
).assign_coords(time=("time", xr.DataArray(np.array(time_iso, dtype="datetime64[ns]"), name="time")))
da = da.rename({"lat": "lat", "lon": "lon"})
# ensure coordinate dims named exactly lat/lon and time
da.to_netcdf('/work/output/mhw_mask.nc', engine="h5netcdf")

report = {
    "region": {"lat_min": 57.83, "lat_max": 59.03, "lon_min": 17.41, "lon_max": 18.61},
    "baseline_analysed": {"start": base_dates[0].isoformat(), "end": base_dates[-1].isoformat()},
    "target_analysed": {"start": tgt_dates[0].isoformat(), "end": tgt_dates[-1].isoformat()},
    "events": [{"onset": e[0].isoformat(), "end": e[1].isoformat()} for e in events],
    "complete": True,
    "caveats": ("Region bounds 57.83-59.03N/17.41-18.61E fall between grid points of the 0.02-deg grid; "
                "cells used are lat 57.84-59.02, lon 17.42-18.60 (60x60). Sea cells: finite SST on all 92 target days "
                "({} of 3600). Thresholds are the hazen (type-5) 90th percentile of the +-5-day baseline pools "
                "(1992-2002 pools, edge windows 1991-12-27..31 and 2003-01-01..05 included), day 60 set to the mean of "
                "days 59 and 61, then 31-day centred wrap-around smoothed; climatology computed analogously but not "
                "needed for detection. Per-cell MHWs: runs of >=5 hot days, gaps of <=2 non-hot days joined. "
                "{} land cells (non-finite) masked as 0.".format(int(sea.sum()), int((~sea).sum()))),
}
json.dump(report, open('/work/output/report.json', 'w'), indent=2)
print("wrote outputs")
print("mask ones:", int(mhw_var.sum()), "active days:", int(active.sum()))
'''
open('/work/mhw_analyse.py', 'w').write(script)
print("written")
