
import fsspec
import xarray as xr
import numpy as np
import datetime as dt
import time

fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'

# Region indices
lat_start, lat_end = 260, 319
lon_start, lon_end = 485, 544

# Test loading a few files to make sure it works
start = time.time()
for date_str in ['19920101', '19920102', '19920103']:
    f = fs.open(f'{base_path}/sst_{date_str}.nc', 'rb')
    ds = xr.open_dataset(f, engine='h5netcdf')
    sst = ds.analysed_sst.values[0, lat_start:lat_end+1, lon_start:lon_end+1]
    ds.close()
    print(f"File {date_str}: shape={sst.shape}, min={np.nanmin(sst)}, max={np.nanmax(sst)}")
elapsed = time.time() - start
print(f"Loading 3 files took {elapsed:.2f}s")
