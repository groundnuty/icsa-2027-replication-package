
import xarray as xr
import fsspec
import numpy as np

fs = fsspec.filesystem('onedata')

# Read from s1z daily file
f1 = fs.open('icsa2027_data_20261101T090944Z/s1z/sst_20080601.nc', 'rb')
ds1 = xr.open_dataset(f1, engine='h5netcdf')

# Read from s2z combined file
f2 = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds2 = xr.open_dataset(f2, engine='h5netcdf')

# Select the same region and date from s2z
region_s2 = ds2.sel(latitude=slice(57.83, 59.03), longitude=slice(17.41, 18.61))
val_s2 = region_s2.analysed_sst.sel(time='2008-06-01').values

# Compare with s1z
val_s1 = ds1.analysed_sst.values[0]

print("s1z shape:", val_s1.shape)
print("s2z shape:", val_s2.shape)
print("Same shape:", val_s1.shape == val_s2.shape)

if val_s1.shape == val_s2.shape:
    diff = np.abs(val_s1 - val_s2)
    print("Max diff:", np.nanmax(diff))
    print("All equal:", np.allclose(val_s1, val_s2, equal_nan=True))

# Also compare lat/lon coords
print("s1z lat:", ds1.latitude.values[:5], "...", ds1.latitude.values[-5:])
print("s2z lat:", region_s2.latitude.values[:5], "...", region_s2.latitude.values[-5:])
