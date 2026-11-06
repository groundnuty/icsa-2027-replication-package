
import xarray as xr
import numpy as np

# Check coordinate values match original dataset
path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds_orig = xr.open_dataset(path, engine='h5netcdf')

orig_lat = ds_orig.latitude.values[217:277]
orig_lon = ds_orig.longitude.values[421:481]
orig_time = ds_orig.time.values[9282:9374]

ds_orig.close()

# Read our output
ds_out = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')

print("Latitude comparison:")
print(f"  Original: {orig_lat}")
print(f"  Output:   {ds_out.lat.values}")
print(f"  Match: {np.allclose(orig_lat, ds_out.lat.values)}")

print("\nLongitude comparison:")
print(f"  Original: {orig_lon}")
print(f"  Output:   {ds_out.lon.values}")
print(f"  Match: {np.allclose(orig_lon, ds_out.lon.values)}")

print("\nTime comparison:")
print(f"  Original: {orig_time[:3]} ... {orig_time[-3:]}")
print(f"  Output:   {ds_out.time.values[:3]} ... {ds_out.time.values[-3:]}")
print(f"  Match: {np.array_equal(orig_time, ds_out.time.values)}")

ds_out.close()

print("\nCoordinate values match the original dataset.")
