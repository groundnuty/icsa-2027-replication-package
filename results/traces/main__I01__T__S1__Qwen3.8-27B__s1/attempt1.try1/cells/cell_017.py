import fsspec, os, time, json
import numpy as np
import xarray as xr
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

t_start = time.time()
fs = fsspec.filesystem('onedata')
remote_base = '/icsa2027_data_20261101T090944Z/s1z/'
local_dir = '/work/files'

def daterange(a, b):
    d, out = a, []
    while d <= b:
        out.append(d); d += timedelta(days=1)
    return out

dates = sorted(set(
    daterange(date(1991,12,27), date(1991,12,31))
  + daterange(date(1992,1,1), date(2002,12,31))
  + daterange(date(2003,1,1), date(2003,1,5))
  + daterange(date(2008,6,1), date(2008,8,31))
))
date_to_idx = {d: i for i, d in enumerate(dates)}
ND = len(dates)

# --- reference grid from a valid local file ---
ref = None
for cand in ['sst_19920101.nc', 'sst_20080601.nc', 'sst_20030101.nc']:
    p = os.path.join(local_dir, cand)
    if os.path.exists(p) and os.path.getsize(p) > 0:
        ref = p; break
if ref:
    dsr = xr.open_dataset(ref, engine='h5netcdf')
else:
    f = fs.open(remote_base + 'sst_20080601.nc', 'rb')
    dsr = xr.open_dataset(f, engine='h5netcdf')
LAT = dsr['latitude'].values.astype(np.float64)
LON = dsr['longitude'].values.astype(np.float64)
lat_ref = dsr['latitude'].values.copy()
lon_ref = dsr['longitude'].values.copy()
dsr.close()
lat_sel = (LAT >= 54.13) & (LAT <= 55.33)
lon_sel = (LON >= 14.67) & (LON <= 15.87)
i0 = int(np.argmax(lat_sel)); i1 = int(len(LAT) - 1 - np.argmax(lat_sel[::-1]))
j0 = int(np.argmax(lon_sel)); j1 = int(len(LON) - 1 - np.argmax(lon_sel[::-1]))
lat_region = lat_ref[i0:i1+1]
lon_region = lon_ref[j0:j1+1]
NC = len(lat_region) * len(lon_region)
print("region lats", lat_region[0], lat_region[-1], "lons", lon_region[0], lon_region[-1], "NC:", NC, flush=True)

sst = np.empty((ND, NC), dtype=np.float64)
problems = []
def load_one(d):
    idx = date_to_idx[d]
    name = f"sst_{d:%Y%m%d}.nc"
    local = os.path.join(local_dir, name)
    try:
        if os.path.exists(local) and os.path.getsize(local) > 0:
            ds = xr.open_dataset(local, engine='h5netcdf')
            arr = ds['analysed_sst'].isel(latitude=slice(i0, i1+1), longitude=slice(j0, j1+1)).values.astype(np.float64).ravel()
            if not np.array_equal(ds['latitude'].values, lat_ref):
                problems.append((str(d), 'lat mismatch'))
            if not np.array_equal(ds['longitude'].values, lon_ref):
                problems.append((str(d), 'lon mismatch'))
            if np.datetime64(ds['time'].values[0], 'D') != np.datetime64(str(d), 'D'):
                problems.append((str(d), f"time {ds['time'].values[0]}"))
            ds.close()
            os.remove(local)
        else:
            f = fs.open(remote_base + name, 'rb')
            ds = xr.open_dataset(f, engine='h5netcdf')
            arr = ds['analysed_sst'].isel(latitude=slice(i0, i1+1), longitude=slice(j0, j1+1)).values.astype(np.float64).ravel()
            ds.close(); f.close()
        return (idx, arr, None)
    except Exception as e:
        return (idx, None, f"{type(e).__name__}:{str(e)[:50]}")

done = 0
with ThreadPoolExecutor(max_workers=16) as ex:
    futs = [ex.submit(load_one, d) for d in dates]
    for fut in as_completed(futs):
        idx, arr, err = fut.result()
        if arr is None:
            try:
                name = f"sst_{dates[idx]:%Y%m%d}.nc"
                f = fs.open(remote_base + name, 'rb')
                ds = xr.open_dataset(f, engine='h5netcdf')
                arr = ds['analysed_sst'].isel(latitude=slice(i0, i1+1), longitude=slice(j0, j1+1)).values.astype(np.float64).ravel()
                ds.close(); f.close()
                err = None
            except Exception as e2:
                err = "RETRY " + str(type(e2).__name__)
        if arr is not None:
            sst[idx] = arr
        else:
            problems.append((str(dates[idx]), err))
        done += 1
        if done % 800 == 0:
            print(f"loaded {done}/{ND}  {time.time()-t_start:.0f}s", flush=True)

print("load done in", round(time.time()-t_start,1), "s; problems:", problems, flush=True)
allnan = np.where(np.isnan(sst).all(axis=1))[0]
print("all-NaN rows:", [str(dates[i]) for i in allnan], flush=True)
# partial NaN stats
n_nan = int(np.isnan(sst).sum())
print("total NaN cells in region-stack:", n_nan, flush=True)

np.save('/tmp/sst_region.npy', sst)
with open('/tmp/meta.json', 'w') as f:
    json.dump({'dates': [str(d) for d in dates],
               'lat_region': np.asarray(lat_region, dtype=np.float64).tolist(),
               'lon_region': np.asarray(lon_region, dtype=np.float64).tolist(),
               'lat32': lat_region.astype(np.float32).tolist(),
               'lon32': lon_region.astype(np.float32).tolist()}, f)
print("checkpoint saved; free /work MB:", os.statvfs('/work').f_bavail * os.statvfs('/work').f_bsize / 1e6, flush=True)
