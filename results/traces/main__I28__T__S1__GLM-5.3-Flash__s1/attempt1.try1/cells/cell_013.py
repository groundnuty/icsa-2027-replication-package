import time, fsspec, xarray as xr, numpy as np
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
latmin, latmax, lonmin, lonmax = 57.85, 59.05, 21.01, 22.21

li = oi = None
def read_sub(nm):
    with fs.open(f'{base}/{nm}','rb') as f:
        ds = xr.open_dataset(f, engine='h5netcdf')
        a = ds.analysed_sst.isel(time=0, latitude=li, longitude=oi).values.astype('float64')
        ds.close()
    return nm, a

# get indices first
with fs.open(f'{base}/sst_20130601.nc','rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    lat = ds.latitude.values.astype('float64'); lon = ds.longitude.values.astype('float64')
    ds.close()
li = np.where((lat>=latmin-1e-9)&(lat<=latmax+1e-9))[0]
oi = np.where((lon>=lonmin-1e-9)&(lon<=lonmax+1e-9))[0]

names = [f'sst_199206{d:02d}.nc' for d in range(1,21)]
for nw in (1, 8, 16):
    t0=time.time()
    with ThreadPoolExecutor(max_workers=nw) as ex:
        res = list(ex.map(read_sub, names))
    dt = time.time()-t0
    print(f"workers={nw}: 20 files in {dt:.2f}s -> {20/dt:.1f} files/s")
