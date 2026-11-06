import fsspec, time, os, json
import numpy as np
import xarray as xr
from datetime import date, timedelta

T0 = time.time()
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

lat = ds.latitude.values.astype(np.float64)
lon = ds.longitude.values.astype(np.float64)
tcal = ds.time.values.astype('datetime64[D]')

# region cells (inclusive bounds)
lm = (lat >= 58.69) & (lat <= 59.89)
lom = (lon >= 18.69) & (lon <= 19.89)
lat_idx = np.where(lm)[0]; lon_idx = nl = np.where(lom)[0]
print("lat cells:", lat_idx.size, lat[lat_idx[0]], "->", lat[lat_idx[-1]])
print("lon cells:", lon_idx.size, lon[lon_idx[0]], "->", lon[lon_idx[-1]])

def di(d):  # date -> time index (full daily sequence)
    return int((np.datetime64(d, 'D') - np.datetime64('1982-01-01', 'D')) / np.timedelta64(1, 'D'))

b0, b1 = di(date(1991,12,27)), di(date(2003,1,5))     # baseline window incl. end extensions
t0i, t1i = di(date(2017,6,1)), di(date(2017,8,31))
nB, nT = b1-b0+1, t1i-t0i+1
print("baseline window days:", nB, tcal[b0], tcal[b1], " target days:", nT, tcal[t0i], tcal[t1i])
# verify time continuity within needed ranges
seg = tcal[b0:b1+1]
print("base seg continuous:", np.all(np.diff(seg.astype('int64')) == 1))
seg2 = tcal[t0i:t1i+1]
print("tgt seg continuous:", np.all(np.diff(seg2.astype('int64')) == 1))

STATE = '/work/read_state.npz'
base = np.full((nB, lat_idx.size, lon_idx.size), np.nan, np.float32)
tgt  = np.full((nT, lat_idx.size, lon_idx.size), np.nan, np.float32)
db, dt_ = 0, 0
if os.path.exists(STATE):
    z = np.load(STATE)
    base, tgt = z['base'], z['tgt']
    db, dt_ = int(z['db']), int(z['dt'])
    print("resuming from db=", db, "dt=", dt_)

sst = ds.analysed_sst
for i in range(b0 + db, b1 + 1):
    base[db] = sst.isel(time=i, latitude=lat_idx, longitude=lon_idx).values
    db += 1
    if db % 500 == 0:
        np.savez(STATE, base=base, tgt=tgt, db=np.int64(db), dt=np.int64(dt_))
        print("base", db, "/", nB, "t=", time.time()-T0, flush=True)
for i in range(t0i + dt_, t1i + 1):
    tgt[dt_] = sst.isel(time=i, latitude=lat_idx, longitude=lon_idx).values
    dt_ += 1
    if dt_ % 50 == 0:
        np.savez(STATE, base=base, tgt=tgt, db=np.int64(db), dt=np.int64(dt_))
        print("tgt", dt_, "/", nT, "t=", time.time()-T0, flush=True)

np.savez('/work/read_done.npz',
         base=base, tgt=tgt,
         lat_vals=lat[lat_idx].astype(np.float32), lon_vals=lon[lon_idx].astype(np.float32),
         b_dates=tcal[b0:b1+1].astype('datetime64[D]'), t_dates=tcal[t0i:t1i+1].astype('datetime64[D]'),
         lat_idx=lat_idx, lon_idx=lon_idx)
print("DONE read. base finite frac:", np.isfinite(base).mean(), " tgt finite frac:", np.isfinite(tgt).mean())
print("elapsed:", time.time()-T0)
