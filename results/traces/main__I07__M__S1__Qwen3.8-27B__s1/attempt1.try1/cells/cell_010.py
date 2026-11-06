import numpy as np, json
from datetime import date, timedelta

z = np.load("/tmp/sst_data.npz")
B, T = z["B"], z["T"]
lat, lon = z["lat"], z["lon"]
btimes, ttimes = z["btimes"], z["ttimes"]

def to_date(ts):
    return date(int(ts[0:4]), int(ts[5:7]), int(ts[8:10]))

base_dates = [to_date(t) for t in btimes]
tgt_dates  = [to_date(t) for t in ttimes]
print("base dates:", base_dates[0], "..", base_dates[-1], len(base_dates))
print("tgt dates :", tgt_dates[0], "..", tgt_dates[-1], len(tgt_dates))

# sanity: file order / times monotonic
assert base_dates == sorted(base_dates) and tgt_dates == sorted(tgt_dates)

def doy(d):  # month/day mapping: Jan1=1 ... Feb29=60 ... Dec31=366
    return (d - date(d.year,1,1)).days + 1

N = B.shape[0]
# M[t, d0]: loaded date t lies within +-5 cal days of a baseline date with doy d0+1
loaded_idx = {d: i for i, d in enumerate(base_dates)}
M = np.zeros((N, 366), dtype=bool)
nbase = 0
for d in base_dates:
    if date(1992,1,1) <= d <= date(2002,12,31):
        nbase += 1
        d0 = doy(d) - 1
        for k in range(-5, 6):
            t = d + timedelta(days=k)
            M[loaded_idx[t], d0] = True
print("baseline dates used:", nbase)
counts = M.sum(axis=0)
print("pool sizes: min", counts.min(), "max", counts.max())
print("day60 col (idx59) count (unused):", counts[59])
print("any col != 121 except idx59:", sorted(set(counts.tolist()) - {121, counts[59]}), "idx59:", counts[59])

# sea cells: finite on every target day
sea = np.isfinite(T).all(axis=0)
print("sea cells:", int(sea.sum()), "of", sea.size)
ncell = sea.sum()
sea_idx = np.where(sea.ravel())[0]

# thresholds & climatology per sea cell, per doy (hazen 90th percentile / mean, NaN-ignoring)
thr = np.full((ncell, 366), np.nan)
clim = np.full((ncell, 366), np.nan)
Bs = B[:, sea.ravel()[:, None] if False else None]  # placeholder
# select sea cells: B shape (N, 60, 60) -> (N, ncell)
Bs = B[:, sea_idx].reshape(N, -1)  # careful: sea_idx indexes flat (lat*lon)
Bs = B[:, :][:, :].reshape(N, 60, 60)[:, sea_idx]  # (N, ncell)
print("Bs shape", Bs.shape)
for d0 in range(366):
    if d0 == 59:
        continue
    mask = M[:, d0]
    vals = Bs[mask]  # (121, ncell)
    thr[:, d0] = np.nanquantile(vals, 0.9, method="hazen", axis=0)
    clim[:, d0] = np.nanmean(vals, axis=0)
# day 60 = mean of 59 and 61
thr[:, 59] = (thr[:, 58] + thr[:, 60]) / 2.0
clim[:, 59] = (clim[:, 58] + clim[:, 60]) / 2.0
print("any NaN left in thr/clim:", np.isnan(thr).any(), np.isnan(clim).any())

# circular centred 31-day moving mean
def smooth31(a):
    s = np.zeros_like(a, dtype=np.float64)
    for k in range(-15, 16):
        s += np.roll(a, k, axis=1)
    return s / 31.0

thr_s = smooth31(thr)
clim_s = smooth31(clim)
print("smooth ok", thr_s.shape)

np.savez("/tmp/step2.npz", thr=thr, clim=clim, thr_s=thr_s, clim_s=clim_s, sea=sea,
         lat=lat, lon=lon, ttimes=ttimes)
print("thr range (K):", thr_s.min(), thr_s.max())
# spot check one cell threshold around Jul 1 (doy 183)
print("sample thr_s cell0 doy 180-186:", thr_s[0, 179:186])
