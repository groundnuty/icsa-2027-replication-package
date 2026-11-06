
import xarray as xr
import numpy as np
import fsspec

# Verify time coordinates match the original dataset
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    # Get original time for target period
    time = ds.time.values
    target_mask = (time >= np.datetime64('2010-06-01')) & (time <= np.datetime64('2010-08-31'))
    orig_time = time[target_mask]
    print("Original dataset target times:", len(orig_time))
    
    # Get original lat/lon for region
    lat = ds.latitude.values
    lon = ds.longitude.values
    lat_mask = (lat >= 58.69) & (lat <= 59.89)
    lon_mask = (lon >= 18.69) & (lon <= 19.89)
    orig_lat = lat[lat_mask]
    orig_lon = lon[lon_mask]
    print("Original lat values in region:", len(orig_lat), orig_lat[0], "to", orig_lat[-1])
    print("Original lon values in region:", len(orig_lon), orig_lon[0], "to", orig_lon[-1])

# Load output
ds_out = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
out_time = ds_out['time'].values
out_lat = ds_out['latitude'].values
out_lon = ds_out['longitude'].values

print("\nOutput time matches original:", np.array_equal(out_time, orig_time))
print("Output lat matches original:", np.array_equal(out_lat, orig_lat))
print("Output lon matches original:", np.array_equal(out_lon, orig_lon))

ds.close()
ds_out.close()
