
import xarray as xr
import numpy as np

# Load the output
ds_out = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
out_lat = ds_out.lat.values
out_lon = ds_out.lon.values
out_time = ds_out.time.values
ds_out.close()

# Load a source file
import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

f = fs.open(f'{base}/sst_20210601.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

lat_all = ds.latitude.values
lon_all = ds.longitude.values

lat_idx = np.where((lat_all >= 61.57) & (lat_all <= 62.77))[0]
lon_idx = np.where((lon_all >= 20.17) & (lon_all <= 21.37))[0]
src_lat = lat_all[lat_idx.min():lat_idx.max()+1]
src_lon = lon_all[lon_idx.min():lon_idx.max()+1]
src_time = ds.time.values
ds.close()
f.close()

print("Lat match:", np.allclose(out_lat, src_lat, equal_nan=True))
print("Lon match:", np.allclose(out_lon, src_lon, equal_nan=True))
print("Time in output:", out_time[0], "to", out_time[-1])
print("Time in source:", src_time[0])

# Check that the time values match what's expected
print("\nOutput time type:", out_time.dtype)
print("Output time first:", out_time[0])
print("Output time last:", out_time[-1])
