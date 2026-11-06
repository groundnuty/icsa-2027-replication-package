
import fsspec
import xarray as xr
import numpy as np

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# Check time coordinate in target files
for f in ['sst_20040601.nc', 'sst_20040831.nc']:
    with fs.open(f'{base}/{f}', 'rb') as fh:
        ds = xr.open_dataset(fh, engine='h5netcdf')
        print(f'{f}: time = {ds["time"].values}')
        ds.close()

# Check our output time
ds_out = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(f'Output time: {ds_out["time"].values[:3]} ... {ds_out["time"].values[-3:]}')
print(f'Output time dtype: {ds_out["time"].dtype}')
print(f'Output time count: {len(ds_out["time"])}')
ds_out.close()
