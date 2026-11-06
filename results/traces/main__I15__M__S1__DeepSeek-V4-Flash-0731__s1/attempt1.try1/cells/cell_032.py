import xarray as xr
import numpy as np

# Verify coordinate values match the original dataset
ds_orig = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20190601.nc', engine='h5netcdf')
lats = ds_orig.latitude.values
lons = ds_orig.longitude.values
ds_orig.close()

ds_out = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')

print("Original lat values in region:")
print(lats[(lats >= 56.13) & (lats <= 57.33)])
print("\nOutput lat values:")
print(ds_out.lat.values)

print("\nOriginal lon values in region:")
print(lons[(lons >= 17.71) & (lons <= 18.91)])
print("\nOutput lon values:")
print(ds_out.lon.values)

# Check they match
lat_match = np.allclose(lats[(lats >= 56.13) & (lats <= 57.33)], ds_out.lat.values)
lon_match = np.allclose(lons[(lons >= 17.71) & (lons <= 18.91)], ds_out.lon.values)
print(f"\nLat match: {lat_match}")
print(f"Lon match: {lon_match}")

# Check time values
print(f"\nOutput time: {ds_out.time.values}")
ds_out.close()
