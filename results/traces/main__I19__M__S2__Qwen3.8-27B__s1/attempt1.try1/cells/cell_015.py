script = r'''
import numpy as np
import xarray as xr
import pandas as pd
import json, os, time as _time

PATH = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
OUT = '/work/output'
os.makedirs(OUT, exist_ok=True)

# ---------------- region ----------------
LAT_MIN, LAT_MAX = 57.13, 58.33
LON_MIN, LON_MAX = 22.79, 23.99
TOL = 1e-6

ds = xr.open_dataset(PATH, engine="h5netcdf")
lat_all = ds.latitude.values.astype(np.float64)
lon_all = ds.longitude.values.astype(np.float64)
mlat = (lat_all >= LAT_MIN - TOL) & (lat_all <= LAT_MAX + TOL)
mlon = (lon_all >= LON_MIN - TOL) & (lon_all <= LON_MAX + TOL)
lat_idx = np.where(mlat)[0]
lon_idx = np.where(mlon)[0]
rlat = lat_all[lat_idx]
rlon = lon_all[lon_idx]
print("region cells:", len(lat_idx), "x", len(lon_idx))

time_all = ds.time.values
# ---------------- date ranges ----------------
def dstr(i): return str(pd.Timestamp(time_all[i]).date())
# find indices by date
def tidx(datestr):
    t = np.datetime64(datestr)
    i = np.searchsorted(time_all, t)
    assert time_all[i] == t, (datestr, t)
    return i

base_start = tidx('1991-12-27')
base_end   = tidx('2003-01-05')
tgt_start  = tidx('2014-06-01')
tgt_end    = tidx('2014-08-31')
print("base days:", dstr(base_start), "to", dstr(base_end), "count", base_end-base_start+1)
print("tgt  days:", dstr(tgt_start), "to", dstr(tgt_end), "count", tgt_end-tgt_start+1)

# ---------------- load data ----------------
base = ds.analysed_sst[base_start:base_end+1, lat_idx, lon_idx].values.astype(np.float64)  # (4027,60,60)
tgt  = ds.analysed_sst[tgt_start:tgt_end+1, lat_idx, lon_idx].values.astype(np.float64)      # (92,60,60)
print("base shape", base.shape, "tgt shape", tgt.shape)
base_dates = pd.to_datetime(time_all[base_start:base_end+1]).strftime('%Y-%m-%d').to_numpy()
tgt_dates  = pd.to_datetime(time_all[tgt_start:tgt_end+1]).strftime('%Y-%m-%d').to_numpy()
date2idx = {d: i for i, d in enumerate(base_dates)}

# ---------------- fixed day-of-year table (leap calendar by month-day) ----------------
mdays = [31,29,31,30,31,30,31,31,30,31,30,31]
cum = np.concatenate(([0], np.cumsum(mdays)))  # cum[m-1] = days before month m
def doy_of(m, d):  # 1..366
    return int(cum[m-1] + d)
inv = {}  # doy -> (m, d)
for m in range(1,13):
    for d in range(1, mdays[m-1]+1):
        inv[doy_of(m,d)] = (m,d)
assert len(inv) == 366 and inv[1]==(1,1) and inv[59]==(2,28) and inv[60]==(2,29) and inv[61]==(3,1) and inv[366]==(12,31)

# ---------------- pool indices per day of year ----------------
from datetime import date, timedelta
pool_idx = {}   # d -> np.array of positions into base_dates
for d in range(1, 367):
    if d == 60:
        continue
    m, dd = inv[d]
    idxs = []
    for Y in range(1992, 2003):
        b = date(Y, m, dd)
        for k in range(-5, 6):
            t = b + timedelta(days=k)
            s = f"{t.year:04d}-{t.month:02d}-{t.day:02d}"
            idxs.append(date2idx[s])
    idxs = np.array(idxs, dtype=np.int64)
    assert len(set(idxs.tolist())) == 121, d  # windows of different years are disjoint
    pool_idx[d] = idxs
print("pools built; sample d=1 first/last dates:", base_dates[pool_idx[1][0]], base_dates[pool_idx[1][-1]])
print("sample d=366 first/last dates:", base_dates[pool_idx[366][0]], base_dates[pool_idx[366][-1]])

ncells = len(lat_idx)*len(lon_idx)
# ---------------- threshold + climatology ----------------
thr = np.full((366, ncells), np.nan)
clim = np.full((366, ncells), np.nan)
t0=_time.time()
allnan_cells_thr = 0
for d in range(1, 367):
    if d == 60:
        continue
    pool = base[pool_idx[d], :, :].reshape(121, ncells)
    with np.errstate(invalid='ignore'):
        th = np.nanquantile(pool, 0.9, method='hazen', axis=0)
        cl = np.nanmean(pool, axis=0)
    thr[d-1] = th
    clim[d-1] = cl
    allnan_cells_thr += int(np.isnan(th).sum())
print("threshold/clim loop done in", round(_time.time()-t0,1), "s; all-NaN pool cell-days:", allnan_cells_thr)

# day 60 = mean of 59 and 61
thr[59] = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])
print("thr day60 NaNs:", int(np.isnan(thr[59]).sum()), "clim day60 NaNs:", int(np.isnan(clim[59]).sum()))

# ---------------- smoothing: centred 31-day, wrap over 366 ----------------
off = np.arange(-15, 16)
idxm = (np.arange(366)[:,None] + off[None,:]) % 366
thr_s = thr[:, idxm].mean(axis=1)   # (366, ncells)
clim_s = clim[:, idxm].mean(axis=1)
print("smoothed NaN cell-days thr:", int(np.isnan(thr_s).sum()), "clim:", int(np.isnan(clim_s).sum()))

np.savez_compressed('/work/interim.npz', thr=thr, clim=clim, thr_s=thr_s, clim_s=clim_s,
                    rlat=rlat, rlon=rlon, tgt=tgt, tgt_dates=tgt_dates,
                    base_dates=base_dates)
print("saved interim")

# quick sanity: thresholds in Celsius for a middle cell, mid-June
c = ncells//2
print("cell", c, "lat/lon:", rlat.flat[c//60], rlon.flat[c%60])
for d in [153, 182, 213, 244]:
    print("doy", d, "thr raw K:", thr[d-1,c], "smooth K:", thr_s[d-1,c], " clim smooth C:", clim_s[d-1,c]-273.15)
'''
with open('/work/pipeline1.py','w') as f:
    f.write(script)
print("written")
