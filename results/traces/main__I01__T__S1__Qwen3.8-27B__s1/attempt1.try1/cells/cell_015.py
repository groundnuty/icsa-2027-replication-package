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
print("ND:", ND, flush=True)

# --- region slice from a reference file ---
ref = os.path.join(local_dir, 'sst_20080601.nc')
dsr = xr.open_dataset(ref, engine='h5netcdf')
LAT = dsr['latitude'].values.astype(np.float64)
LON = dsr['longitude'].values.astype(np.float64)
TREF = dsr['time'].values[0]
dsr.close()
lat_sel = (LAT >= 54.13) & (LAT <= 55.33)
lon_sel = (LON >= 14.67) & (LON <= 15.87)
i0 = int(np.argmax(lat_sel)); i1 = int(len(LAT) - 1 - np.argmax(lat_sel[::-1]))
j0 = int(np.argmax(lon_sel)); j1 = int(len(LON) - 1 - np.argmax(lon_sel[::-1]))
lat_region = LAT[i0:i1+1].astype(np.float32)
lon_region = LON[j0:j1+1].astype(np.float32)
NC = len(lat_region) * len(lon_region)
print("region:", lat_region[0], lat_region[-1], lon_region[0], lon_region[-1], "NC:", NC, flush=True)

sst = np.empty((ND, NC), dtype=np.float64)
problems = []
def load_one(d):
    idx = date_to_idx[d]
    name = f"sst_{d:%Y%m%d}.nc"
    local = os.path.join(local_dir, name)
    try:
        if os.path.exists(local) and os.path.getsize(local) > 0:
            ds = xr.open_dataset(local, engine='h5netcdf')
            lat_ok = np.array_equal(ds['latitude'].values.astype(np.float64), LAT)
            lon_ok = np.array_equal(ds['longitude'].values.astype(np.float64), LON)
            tv = ds['time'].values[0]
            arr = ds['analysed_sst'].isel(latitude=slice(i0, i1+1), longitude=slice(j0, j1+1)).values.astype(np.float64).ravel()
            ds.close()
            os.remove(local)
            if not (lat_ok and lon_ok):
                problems.append((str(d), 'grid mismatch'))
            if np.datetime64(tv, 'D') != np.datetime64(str(d), 'D'):
                problems.append((str(d), f"time {tv} != {d}"))
        else:
            f = fs.open(remote_base + name, 'rb')
            ds = xr.open_dataset(f, engine='h5netcdf')
            arr = ds['analysed_sst'].isel(latitude=slice(i0, i1+1), longitude=slice(j0, j1+1)).values.astype(np.float64).ravel()
            ds.close(); f.close()
    except Exception as e:
        problems.append((str(d), type(e).__name__ + ':' + str(e)[:60]))
        return (idx, None, d)
    return (idx, arr, d)

done = 0
with ThreadPoolExecutor(max_workers=16) as ex:
    futs = [ex.submit(load_one, d) for d in dates]
    for fut in as_completed(futs):
        idx, arr, d = fut.result()
        if arr is not None:
            sst[idx] = arr
        else:
            # one retry from remote
            try:
                name = f"sst_{d:%Y%m%d}.nc"
                f = fs.open(remote_base + name, 'rb')
                ds = xr.open_dataset(f, engine='h5netcdf')
                arr = ds['analysed_sst'].isel(latitude=slice(i0, i1+1), longitude=slice(j0, j1+1)).values.astype(np.float64).ravel()
                ds.close(); f.close()
                sst[idx] = arr
                problems = [p for p in problems if p[0] != str(d)]
            except Exception as e2:
                problems.append((str(d), 'RETRY FAIL ' + type(e2).__name__))
        done += 1
        if done % 800 == 0:
            print(f"loaded {done}/{ND}  {time.time()-t_start:.0f}s", flush=True)

print("load done in", round(time.time()-t_start,1), "s", flush=True)
print("problems:", problems[:20], "n:", len(problems), flush=True)
nan_rows = np.isnan(sst).all(axis=1)
print("all-NaN rows:", dates[np.where(nan_rows)[0]][:10], "n:", int(nan_rows.sum()), flush=True)

# persist state for next steps (in case)
np.save('/work/sst_region.npy', sst)
with open('/work/meta.json', 'w') as f:
    json.dump({'dates': [str(d) for d in dates], 'lat_region': lat_region.tolist(),
               'lon_region': lon_region.tolist(), 'problems': [list(p) for p in problems]}, f)
print("saved sst_region.npy, mem MB:", sst.nbytes/1e6, flush=True)
