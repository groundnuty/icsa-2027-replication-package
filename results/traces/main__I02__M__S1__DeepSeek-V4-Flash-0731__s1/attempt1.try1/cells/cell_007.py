
import xarray as xr
import numpy as np
import os

# Check if all files have same dimensions by sampling a few
files = sorted(os.listdir('/data/icsa2027_data_20261101T090944Z/s1z'))
print(f"Total files: {len(files)}")

# Check a few different years
for f in ['sst_19920101.nc', 'sst_19991231.nc', 'sst_20000601.nc', 'sst_20040201.nc']:
    ds = xr.open_dataset(f'/data/icsa2027_data_20261101T090944Z/s1z/{f}', engine='h5netcdf')
    print(f"{f}: shape={ds['analysed_sst'].shape}, lat={ds.latitude.values[0]:.2f}..{ds.latitude.values[-1]:.2f}, lon={ds.longitude.values[0]:.2f}..{ds.longitude.values[-1]:.2f}")
    ds.close()
