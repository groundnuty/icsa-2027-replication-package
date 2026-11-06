
import time
import os
import xarray as xr

base_dir = '/data/icsa2027_data_20261101T090944Z/s1z'
f = os.path.join(base_dir, 'sst_20030601.nc')

# Test xarray
start = time.time()
ds = xr.open_dataset(f, engine='h5netcdf')
sst = ds.analysed_sst.values
ds.close()
print(f"xarray read full: {time.time()-start:.3f}s, shape: {sst.shape}")

# Test xarray with selection
start = time.time()
ds = xr.open_dataset(f, engine='h5netcdf')
sst_sub = ds.analysed_sst.isel(time=0, latitude=slice(330,390), longitude=slice(551,611)).values
ds.close()
print(f"xarray isel: {time.time()-start:.3f}s, shape: {sst_sub.shape}")

# Test netCDF4
try:
    import netCDF4
    start = time.time()
    nc = netCDF4.Dataset(f)
    sst_nc = nc.variables['analysed_sst'][0, 330:390, 551:611]
    nc.close()
    print(f"netCDF4: {time.time()-start:.3f}s, shape: {sst_nc.shape}")
except Exception as e:
    print(f"netCDF4 error: {e}")

# Test h5py or other
try:
    import h5py
    start = time.time()
    with h5py.File(f, 'r') as h5:
        sst_h5 = h5['analysed_sst'][0, 330:390, 551:611]
    print(f"h5py: {time.time()-start:.3f}s, shape: {sst_h5.shape}")
except Exception as e:
    print(f"h5py error: {e}")
