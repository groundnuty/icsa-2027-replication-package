import time, fsspec, xarray as xr, numpy as np, h5py
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

t0 = time.time()
with fs.open(f'{base}/sst_20210615.nc', 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    da = ds['analysed_sst']
    sub = da[0, 130:190, 78:138].values
print('read sub time:', time.time()-t0, 's; shape', sub.shape)

# inspect hdf5 storage/chunks
with fs.open(f'{base}/sst_20210615.nc', 'rb') as f:
    with h5py.File(f, 'r') as h:
        d = h['analysed_sst']
        print('chunks:', d.chunks, 'compression:', d.compression, 'shape:', d.shape)
        print('lat chunks:', h['latitude'].chunks)

# time 10 sequential reads
t0 = time.time()
for dstr in ['19920601','19920602','19920603','19920604','19920605','19920606','19920607','19920608','19920609','19920610']:
    with fs.open(f'{base}/sst_{dstr}.nc', 'rb') as f:
        ds = xr.open_dataset(f, engine='h5netcdf')
        sub = ds['analysed_sst'][0, 130:190, 78:138].values
print('10 reads time:', time.time()-t0, 's')

import netCDF4
print('netCDF4 version:', netCDF4.__version__)
import scipy
print('scipy', scipy.__version__)
print('numpy', np.__version__)