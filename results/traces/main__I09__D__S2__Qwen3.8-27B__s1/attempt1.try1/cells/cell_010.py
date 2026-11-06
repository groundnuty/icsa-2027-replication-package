import numpy as np
import pandas as pd
import xarray as xr
import time as _time
import warnings, os
warnings.filterwarnings('ignore', category=RuntimeWarning)

os.makedirs('/work/output', exist_ok=True)
T = _time.time()

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat_all = ds.latitude.values
lon_all = ds.longitude.values
t_all = ds.time.values

eps = 1e-6
il = np.where((lat_all >= 54.81 - eps) & (lat_all <= 56.01 + eps))[0]
ij = np.where((lon_all >= 19.61 - eps) & (lon_all <= 20.81 + eps))[0]
lat = lat_all[il].astype(np.float32)
lon = lon_all[ij].astype(np.float32)
NL, NJ = len(il), len(ij)
NC = NL * NJ

def sel_time(d0, d1):
    return np.searchsorted(t_all, np.datetime64(d0)), np.searchsorted(t_all, np.datetime64(d1))

def get_sst(a, b):
    arr = ds.analysed_sst.isel(time=slice(a, b+1),
                               latitude=slice(il[0], il[-1]+1),
                               longitude=slice(ij[0], ij[-1]+1)).values
    return arr.astype(np.float64)

b0, b1 = sel_time('1991-12-27', '2003-01-05')
u0, u1 = sel_time('2022-06-01', '2022-08-31')
t_ext = t_all[b0:b1+1]
t_tgt = t_all[u0:u1+1]
S_ext = get_sst(b0, b1)
S_tgt = get_sst(u0, u1)
ds.close()
print("loaded:", S_ext.shape, S_tgt.shape, round(_time.time()-T,1), "s")

def doy_of(t64):
    tt = pd.to_datetime(t64)
    m = tt.month.to_numpy(); d = tt.day.to_numpy()
    ref = pd.to_datetime(dict(year=2020, month=m, day=d)) - pd.Timestamp('2020-01-01')
    return ref.dt.days.to_numpy() + 1

doy_ext = doy_of(t_ext)
doy_tgt = doy_of(t_tgt)

in_base = (t_ext >= np.datetime64('1992-01-01')) & (t_ext <= np.datetime64('2002-12-31'))
base_idx = np.flatnonzero(in_base)
doy_base = doy_ext[base_idx]

thr = np.empty((366, NC), dtype=np.float64)
clim = np.empty((366, NC), dtype=np.float64)
t_base = _time.time()
for d in range(1, 367):
    bi = base_idx[doy_base == d]
    offs = np.unique(np.concatenate([np.arange(k-5, k+6) for k in bi]))
    pool = S_ext[offs].reshape(len(offs), NC)
    thr[d-1] = np.nanquantile(pool, 0.9, axis=0, method='hazen')
    clim[d-1] = np.nanmean(pool, axis=0)
print("pool loop:", round(_time.time()-t_base,1), "s")

thr[59] = 0.5 * (thr[58] + thr[60])
clim[59] = 0.5 * (clim[58] + clim[60])

def circ31(a):
    ext = np.concatenate([a[-15:], a, a[:15]], axis=0)
    w = np.lib.stride_tricks.sliding_window_view(ext, 31, axis=0)
    return w.mean(axis=-1)

thr_s = circ31(thr)
clim_s = circ31(clim)
print("smoothed, total", round(_time.time()-T,1), "s")

fin_tgt = np.isfinite(S_tgt)
sea = fin_tgt.all(axis=0)
n_sea = int(sea.sum())
print("sea cells:", n_sea, "of", NC)

ST = S_tgt.reshape(92, NC)
H = ST >= thr_s[doy_tgt][:, :]
H[:, ~sea.ravel()] = False
print("hot-day fraction (sea cells):", round(float(H[:, sea.ravel()].mean()), 5))

M = np.zeros((92, NC), dtype=np.uint8)
def runs_of_ones(x):
    d = np.diff(np.concatenate(([0], x, [0])))
    return np.flatnonzero(d == 1), np.flatnonzero(d == -1) - 1

for c in range(NC):
    if not sea.ravel()[c]:
        continue
    s, e = runs_of_ones(H[:, c].view(np.int8))
    keep = (e - s + 1) >= 5
    s, e = s[keep], e[keep]
    merged = []
    for a, b in zip(s, e):
        if merged and a - merged[-1][1] - 1 <= 2:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    for a, b in merged:
        M[a:b+1, c] = 1

print("mask days-on:", int(M.sum()), "total", round(_time.time()-T,1), "s")

active = M.any(axis=1)
s, e = runs_of_ones(active.view(np.int8))
events = [(str(t_tgt[a].astype('datetime64[D]')), str(t_tgt[b].astype('datetime64[D]'))) for a, b in zip(s, e)]
print("regional events:", len(events))
for ev in events:
    print("  ", ev)

np.savez('/work/intermediate.npz', thr=thr, clim=clim, thr_s=thr_s, clim_s=clim_s,
         M=M, doy_tgt=doy_tgt, lat=lat, lon=lon,
         t_tgt=t_tgt.astype('datetime64[D]'))
print("saved intermediates")
