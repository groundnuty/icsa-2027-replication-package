import os, json, time
import numpy as np
import xarray as xr
import datetime as dt

with open('/work/required_dates.json') as f:
    dates = [dt.date.fromisoformat(s) for s in json.load(f)]
print("dates:", len(dates), dates[0], dates[-1])

base_end = dt.date(2003,1,5)
tgt_start = dt.date(2019,6,1)
# split indices
n_base = 0
while n_base < len(dates) and dates[n_base] <= base_end:
    n_base += 1
print("base days:", n_base, "tgt days:", len(dates)-n_base)

# region slice from the sample
ds0 = xr.open_dataset('/work/data/sst_20190601.nc', engine='h5netcdf')
lat = ds0['latitude'].values.astype(np.float64)
lon = ds0['longitude'].values.astype(np.float64)
latm = (lat >= 64.39) & (lat <= 65.59)
lonm = (lon >= 23.41) & (lon <= 24.61)
i_lat = np.where(latm)[0]; i_lon = np.where(lonm)[0]
print("n lat:", i_lat.size, "n lon:", i_lon.size)
reg_lat = lat[i_lat]; reg_lon = lon[i_lon]
print("lat:", reg_lat[0], reg_lat[-1], "lon:", reg_lon[0], reg_lon[-1])
ds0.close()

nC = i_lat.size * i_lon.size
S_base = np.empty((n_base, nC), dtype=np.float64)
S_tgt  = np.empty((len(dates)-n_base, nC), dtype=np.float64)

t0 = time.time()
for i, d in enumerate(dates):
    p = f"/work/data/sst_{d.strftime('%Y%m%d')}.nc"
    with xr.open_dataset(p, engine='h5netcdf') as ds:
        v = ds['analysed_sst'].values[i_lat[0] if False else 0, i_lat[:,None], i_lon[None,:]]
    v = np.asarray(v, dtype=np.float64).ravel()
    if i < n_base:
        S_base[i] = v
    else:
        S_tgt[i-n_base] = v
    if i % 500 == 0:
        print(i, time.time()-t0, flush=True)
print("load done", time.time()-t0)
np.savez_compressed('/work/S.npz', S_base=S_base, S_tgt=S_tgt,
                    reg_lat=reg_lat, reg_lon=reg_lon,
                    dates=[d.strftime('%Y-%m-%d') for d in dates])
print("saved; base shape", S_base.shape, "tgt shape", S_tgt.shape)
print("tgt finite per cell: min/max", np.isfinite(S_tgt).all(axis=0).sum(), "cells fully finite")
