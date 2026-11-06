
import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
p = '/icsa2027_data_20261101T090944Z/s1z/sst_20080701.nc'

# whole file
t0=time.time()
f = fs.open(p, "rb")
ds = xr.open_dataset(f, engine="h5netcdf")
a = ds['analysed_sst'].values
t1=time.time()
print("whole file read+decode:", t1-t0, "s", a.shape)
f.close()

# region slice
t0=time.time()
f = fs.open(p, "rb")
ds = xr.open_dataset(f, engine="h5netcdf")
sub = ds['analysed_sst'].isel(latitude=slice(217,277), longitude=slice(421,481)).values
t1=time.time()
print("region slice read:", t1-t0, "s", sub.shape)
f.close()
