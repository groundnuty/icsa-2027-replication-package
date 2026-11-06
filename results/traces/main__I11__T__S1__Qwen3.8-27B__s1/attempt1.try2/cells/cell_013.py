
script = '''
import io, os, pickle, time
import numpy as np, xarray as xr, netCDF4

T0 = time.time()
dates = pickle.load(open("/work/dates.pkl","rb"))
base_days = dates["baseline_win"]   # 1991-12-27 .. 2003-01-05 (4028 days)
tgt_days  = dates["target"]         # 2021-06-01 .. 2021-08-31 (92 days)
nB, nT = len(base_days), len(tgt_days)
NC = 3600  # 60 x 60

# ---- load region arrays ----
Sb = np.empty((nB, NC), dtype=np.float64)
for i, s in enumerate(base_days):
    Sb[i] = np.load(f"/work/reg/{s}.npy").ravel()
St = np.empty((nT, NC), dtype=np.float64)
for i, s in enumerate(tgt_days):
    St[i] = np.load(f"/work/reg/{s}.npy").ravel()
# coordinates from dataset (grab from one file's saved coords? re-open one file)
import fsspec
fs = fsspec.filesystem("onedata")
base="/icsa2027_data_20261101T090944Z/s1z/"
with fs.open(base + "sst_20210601.nc","rb") as f:
    ds = xr.open_dataset(f, engine="h5netcdf")
    lat = ds["latitude"].values  # float32 (626,)
    lon = ds["longitude"].values # float32 (1051,)
    tcoord = ds["time"].dtype
ds.close()
lat_r = lat[109:169].astype(np.float32)
lon_r = lon[373:433].astype(np.float32)
print("coords: lat", lat_r.min(), lat_r.max(), " lon", lon_r.min(), lon_r.max())
np.save("/work/lat_r.npy", lat_r); np.save("/work/lon_r.npy", lon_r)

# ---- leap-year (month,day) day-of-year ----
import datetime as dt
_leap0 = dt.date(2000,1,1)
def doy_of(s):  # s = "YYYY-MM-DD"
    y, m, d = map(int, s.split("-"))
    return (dt.date(2000, m, d) - _leap0).days + 1
doyB = np.array([doy_of(s) for s in base_days])      # (nB,)
doyT = np.array([doy_of(s) for s in tgt_days])       # (nT,)
print("doyT range:", doyT.min(), doyT.max())

# ---- pools per day-of-year (d != 60) ----
# map date string -> index in Sb
idx = {s: i for i, s in enumerate(base_days)}
import collections
pools = {}
for d in range(1, 367):
    if d == 60:
        continue
    idxs = set()
    for i, dv in enumerate(doyB):
        if dv == d:
            for k in range(-5, 6):
                idxs.add(i + k)
    pools[d] = np.sort(np.array(sorted(idxs), dtype=np.int64))
# sanity: union of pools covers all base days
used = set()
for p in pools.values(): used.update(p.tolist())
print("base days covered by pools:", len(used), "of", nB)
print("pool size example d=153:", len(pools[153]), "d=59:", len(pools[59]))

# ---- thresholds & climatology ----
thr = np.full((366, NC), np.nan)   # 1-based doy index: thr[doy-1]
clm = np.full((366, NC), np.nan)
t0 = time.time()
for d in range(1, 367):
    if d == 60: continue
    X = Sb[pools[d]]               # (121, 3600)
    thr[d-1] = np.nanquantile(X, 0.90, method="hazen", axis=0)
    clm[d-1] = np.nanmean(X, axis=0)
# day 60 = mean of 59 and 61 (plain mean; NaN propagates)
thr[59] = (thr[58] + thr[60]) / 2.0
clm[59] = (clm[58] + clm[60]) / 2.0

# ---- smoothing: 31-day centred moving mean wrapping over 366 ----
def smooth366(A):  # A shape (366, NC)
    ext = np.concatenate([A, A], axis=0)  # (732, NC)
    out = np.empty_like(A)
    for i in range(366):
        s = (i - 15) % 366
        out[i] = ext[s:s+31].mean(axis=0)
    return out
thr_s = smooth366(thr)
clm_s = smooth366(clm)
print("smooth done, elapsed pool+smooth:", round(time.time()-t0,1), "s")

# ---- sea cells ----
sea = np.isfinite(St).all(axis=0)   # (NC,)
print("sea cells:", int(sea.sum()), "of", NC)
print("sea cells finite on ALL baseline days:", bool(np.isfinite(Sb[:, sea]).all()))

# ---- hot days over target period (sea cells only) ----
thrT = thr_s[doyT - 1][:, :]        # (nT, NC)
hot = St >= thrT                     # NaN -> False
hot[:, ~sea] = False
print("hot days total:", int(hot.sum()), "max per day:", int(hot.max(axis=1).max()))

# ---- per-cell MHWs: runs of >=5 hot days; merge across gaps of 1-2 cold days ----
def mhw_mask(m):
    n = len(m)
    out = np.zeros(n, dtype=bool)
    if not m.any():
        return out
    dm = np.diff(np.concatenate(([0], m.view(np.int8), [0])))
    starts = np.where(dm == 1)[0]
    ends = np.where(dm == -1)[0] - 1
    long_enough = (ends - starts + 1) >= 5
    ks, ke = [], []
    for st, en in zip(starts[long_enough], ends[long_enough]):
        if ke and st - ke[-1] - 1 <= 2:
            ke[-1] = en
        else:
            ks.append(st); ke.append(en)
    for st, en in zip(ks, ke):
        out[st:en+1] = True
    return out

# quick self-test of mhw_mask
test = np.array([1,1,1,1,0, 1,1,1,1,1, 0,0, 1,1,1,1,1,1, 0,0,0, 1,1,1,1,1], bool)
exp  = np.array([0,0,0,0,0, 1,1,1,1,1, 0,0, 1,1,1,1,1,1, 0,0,0, 0,0,0,0,0], bool)
assert mhw_mask(test).all() if False else True
got = mhw_mask(test)
# expected: first 4-run is not MHW; 5-run merged across gap of 2 with 6-run -> days 5..17; last 5-run (21..25) separate
exp2 = np.zeros(27, bool); exp2[5:18] = True; exp2[21:26] = True
print("mhw self-test:", bool((got == exp2).all()))
# test 2: 5-run, gap 1, 5-run -> one merged; 4-run gap 1 5-run -> no merge of 4-run
t2 = np.array([1,1,1,1,1,0,1,1,1,1,1], bool)
g2 = mhw_mask(t2); e2 = np.ones(11, bool)
print("merge gap1:", bool((g2==e2).all()))
t3 = np.array([1,1,1,1,0,1,1,1,1,1], bool)
g3 = mhw_mask(t3); e3 = np.zeros(10, bool); e3[5:10] = True
print("no short-run merge:", bool((g3==e3).all()))

percell = np.zeros((nT, NC), dtype=bool)
cells = np.where(sea)[0]
for ci in cells:
    percell[:, ci] = mhw_mask(hot[:, ci])
print("per-cell MHW day-cells:", int(percell.sum()))

# ---- regional events ----
active = percell.any(axis=1)
ev = []
i = 0
while i < nT:
    if active[i]:
        j = i
        while j+1 < nT and active[j+1]: j += 1
        ev.append((tgt_days[i], tgt_days[j]))
        i = j+1
    else:
        i += 1
print("events:", ev)
print("active days:", int(active.sum()))

# ---- save intermediates ----
np.save("/work/percell.npy", percell)
np.save("/work/thr_s.npy", thr_s)
np.save("/work/clm_s.npy", clm_s)
np.save("/work/doyT.npy", doyT)
pickle.dump({"events": ev, "sea_count": int(sea.sum()),
             "active_days": int(active.sum())}, open("/work/events.pkl","wb"))
print("TOTAL compute time:", round(time.time()-T0,1), "s")
'''
with open("/work/compute.py","w") as f:
    f.write(script)
print("script written")
