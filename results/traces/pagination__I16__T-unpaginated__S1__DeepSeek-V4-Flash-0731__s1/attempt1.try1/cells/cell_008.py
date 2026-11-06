
import fsspec
import xarray as xr
import numpy as np

fs = fsspec.filesystem('onedata')

# Check a few files to confirm consistent grid
for name in ['sst_19920101.nc', 'sst_20000601.nc', 'sst_20020831.nc', 'sst_20080601.nc', 'sst_20080831.nc']:
    path = f'icsa2027_data_20261101T090944Z/s1z/{name}'
    f = fs.open(path, 'rb')
    ds = xr.open_dataset(f, engine='h5netcdf')
    print(f'{name}: lat shape={ds.latitude.shape}, lon shape={ds.longitude.shape}, time={ds.time.values}')
    print(f'  lat range: {ds.latitude.values[0]:.2f} to {ds.latitude.values[-1]:.2f}')
    print(f'  lon range: {ds.longitude.values[0]:.2f} to {ds.longitude.values[-1]:.2f}')
    print(f'  data shape: {ds.analysed_sst.shape}')
