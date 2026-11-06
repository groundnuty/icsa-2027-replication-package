
import fsspec
import xarray as xr
import numpy as np
import datetime, time

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

lat_min_i, lat_max_i = 404, 463
lon_min_i, lon_max_i = 559, 618

# Test loading a few files
start = time.time()
data_list = []
for i in range(10):
    d = datetime.date(1992, 1, 1) + datetime.timedelta(days=i)
    fpath = f'{base}/sst_{d.strftime("%Y%m%d")}.nc'
    f = fs.open(fpath, 'rb')
    ds = xr.open_dataset(f, engine='h5netcdf')
    region = ds.analysed_sst.values[0, lat_min_i:lat_max_i+1, lon_min_i:lon_max_i+1]
    data_list.append(region)
    ds.close()
    f.close()
elapsed = time.time() - start
print(f"Loaded {len(data_list)} files in {elapsed:.2f}s")
print(f"Region shape: {data_list[0].shape}")
print(f"Sample: {data_list[0][:2, :2]}")
