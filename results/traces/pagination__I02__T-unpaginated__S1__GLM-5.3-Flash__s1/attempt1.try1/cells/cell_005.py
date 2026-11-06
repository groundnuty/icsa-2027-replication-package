import fsspec, xarray as xr, numpy as np, time
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
import datetime as dt

i0,i1,j0,j1 = 34, 94, 213, 273  # placeholder, will confirm

def read_one(day):
    p = f'{base}/sst_{day:%Y%m%d}.nc'
    with fs.open(p,'rb') as f:
        ds = xr.open_dataset(f, engine='h5netcdf')
        v = ds['analysed_sst'].isel(time=0, latitude=slice(i0,i1), longitude=slice(j0,j1)).values
        t = ds['time'].values[0]
        lat_ = ds['latitude'].isel(latitude=slice(i0,i1)).values
        lon_ = ds['longitude'].isel(longitude=slice(j0,j1)).values
        ds.close()
    return t, v, lat_, lon_

days = [dt.date(2004,6,1)+dt.timedelta(days=k) for k in range(12)]
t0=time.time()
with ThreadPoolExecutor(12) as ex:
    res = list(ex.map(read_one, days))
dtv = time.time()-t0
print(f"12 files, 12 threads: {dtv:.2f}s -> {12/dtv:.1f} files/s")
print("times:", [str(r[0])[:10] for r in res[:3]], [str(r[0])[:10] for r in res[-2:]])
latref, lonref = res[0][2], res[0][3]
print("grid identical across files:", all(np.array_equal(r[2],latref) and np.array_equal(r[3],lonref) for r in res))
v = res[0][1]
print("shape:", v.shape, "dtype:", v.dtype, "finite frac:", np.isfinite(v).mean())
print("sample min/max (finite):", np.nanmin(v), np.nanmax(v))
