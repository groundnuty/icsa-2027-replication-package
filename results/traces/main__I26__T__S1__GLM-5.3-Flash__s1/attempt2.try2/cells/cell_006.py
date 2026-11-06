import fsspec, xarray as xr, numpy as np, io, time
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
dates = ['1992%02d%02d'%(6,d) for d in range(1,11)]

# Approach A: fs.cat list -> BytesIO
t0=time.time()
data = fs.cat([f'{base}/sst_{d}.nc' for d in dates])
t1=time.time()
print('cat 10 files:', t1-t0)
for d in dates[:3]:
    with xr.open_dataset(io.BytesIO(data[f'{base}/sst_{d}.nc']), engine='h5netcdf') as ds:
        v = ds['analysed_sst'].isel(time=0, latitude=slice(200,260), longitude=slice(300,360)).values
t2=time.time()
print('decode 3:', t2-t1)

# Approach B: threaded open
from concurrent.futures import ThreadPoolExecutor
def load(d):
    with fs.open(f'{base}/sst_{d}.nc','rb') as f:
        with xr.open_dataset(f, engine='h5netcdf') as ds:
            return ds['analysed_sst'].isel(time=0, latitude=slice(200,260), longitude=slice(300,360)).values
t3=time.time()
with ThreadPoolExecutor(8) as ex:
    res = list(ex.map(load, dates))
t4=time.time()
print('threaded open 10:', t4-t3)
