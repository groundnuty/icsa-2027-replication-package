
import fsspec
import xarray as xr
import numpy as np
import datetime
import time

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# Test reading 10 files
start = time.time()
for i in range(1, 11):
    date_str = f"199201{i:02d}"
    f = fs.open(f'{base}/sst_{date_str}.nc', 'rb')
    ds = xr.open_dataset(f, engine='h5netcdf')
    sst = ds.analysed_sst.values[0, 330:390, 551:611]
    ds.close()
    f.close()
elapsed = time.time() - start
print(f"Time to read 10 files: {elapsed:.2f}s, avg per file: {elapsed/10:.2f}s")
