
import fsspec
import xarray as xr
import numpy as np
import time

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# Test loading a single file and extracting the region
start = time.time()
path = f'{base}/sst_20210601.nc'
with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    # Extract region: lat indices 48-107, lon indices 353-412
    sst = ds.analysed_sst.values[0, 48:108, 353:413]
print(f"Loaded in {time.time()-start:.2f}s")
print("Shape:", sst.shape)
print("NaN count:", np.isnan(sst).sum())
print("Min/Max:", np.nanmin(sst), np.nanmax(sst))
