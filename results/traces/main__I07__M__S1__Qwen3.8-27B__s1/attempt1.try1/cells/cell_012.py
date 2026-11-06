import numpy as np, json
from datetime import date, timedelta

z = np.load("/tmp/sst_data.npz")
B, T = z["B"], z["T"]
lat, lon = z["lat"], z["lon"]
btimes, ttimes = z["btimes"], z["ttimes"]

def to_date(ts):
    s = str(ts)
    return date(int(s[0:4]), int(s[5:7]), int(s[8:10]))
base_dates = [to_date(t) for t in btimes]
tgt_dates  = [to_date(t) for t in ttimes]
def doy(d):
    return (d - date(d.year,1,1)).days + 1

N = B.shape[0]
loaded_idx = {d: i for i, d in enumerate(base_dates)}
M = np.zeros((N, 366), dtype=bool)
for d in base_dates:
    if date(1992,1,1) <= d <= date(2002,12,31):
        d0 = doy(d) - 1
        for k in range(-5, 6):
            M[loaded_idx[d + timedelta(days=k)], d0] = True

sea = np.isfinite(T).all(axis=0)
ncell = int(sea.sum())
sea_idx = np.where(sea.ravel())[0]
Bs = B.reshape(N, 60*60)[:, sea_idx]   # (N, ncell), C-order matches ravel
print("sea cells:", ncell, "Bs", Bs.shape)

thr = np.full((ncell, 366), np.nan)
clim = np.full((ncell, 366), np.nan)
for d0 in range(366):
    if d0 == 59:
        continue
    vals = Bs[M[:, d0]]
    assert vals.shape[0] == 121
    thr[:, d0] = np.nanquantile(vals, 0.9, method="hazen", axis=0)
    clim[:, d0] = np.nanmean(vals, axis=0)
thr[:, 59] = (thr[:, 58] + thr[:, 60]) / 2.0
clim[:, 59] = (clim[:, 58] + clim[:, 60]) / 2.0
print("any NaN left in thr/clim:", np.isnan(thr).any(), np.isnan(clim).any())

def smooth31(a):
    s = np.zeros_like(a, dtype=np.float64)
    for k in range(-15, 16):
        s += np.roll(a, k, axis=1)
    return s / 31.0

thr_s = smooth31(thr)
clim_s = smooth31(clim)
print("thr range (K):", thr_s.min(), thr_s.max(), " clim range:", clim_s.min(), clim_s.max())
np.savez("/tmp/step2.npz", thr=thr, clim=clim, thr_s=thr_s, clim_s=clim_s, sea=sea,
         lat=lat, lon=lon, ttimes=ttimes)
print("saved step2")
