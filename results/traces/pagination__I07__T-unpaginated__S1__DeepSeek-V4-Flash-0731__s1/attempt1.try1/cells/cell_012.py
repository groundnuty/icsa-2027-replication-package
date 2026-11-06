
import fsspec
import xarray as xr
import numpy as np
import time
import datetime

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# Test loading 10 files sequentially
dates = []
d = datetime.date(1992, 1, 1)
for _ in range(10):
    dates.append(d)
    d += datetime.timedelta(days=1)

lat_start, lat_end = 48, 108
lon_start, lon_end = 353, 413

start = time.time()
for date in dates:
    path = f'{base}/sst_{date.strftime("%Y%m%d")}.nc'
    with fs.open(path, 'rb') as f:
        ds = xr.open_dataset(f, engine='h5netcdf')
        sst = ds.analysed_sst.values[0, lat_start:lat_end, lon_start:lon_end]
elapsed = time.time() - start
print(f"Loaded {len(dates)} files in {elapsed:.2f}s = {elapsed/len(dates):.2f}s per file")
print(f"Estimated time for 4028 files: {elapsed/len(dates)*4028/60:.1f} minutes")
