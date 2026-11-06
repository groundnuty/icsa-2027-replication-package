
import xarray as xr
import numpy as np

# Load the original dataset to get coordinates
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Region bounds
lat_min, lat_max = 61.57, 62.77
lon_min, lon_max = 20.17, 21.37

lat_vals = ds.latitude.values
lon_vals = ds.longitude.values
lat_mask = (lat_vals >= lat_min) & (lat_vals <= lat_max)
lon_mask = (lon_vals >= lon_min) & (lon_vals <= lon_max)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]

region_lat = ds.latitude.values[lat_idx]
region_lon = ds.longitude.values[lon_idx]

# Target time indices
times = ds.time.values
targ_mask = (times >= np.datetime64('2009-06-01')) & (times <= np.datetime64('2009-08-31'))
targ_time_vals = times[targ_mask]

print(f"Region lat: {region_lat[0]} to {region_lat[-1]}, {len(region_lat)} values")
print(f"Region lon: {region_lon[0]} to {region_lon[-1]}, {len(region_lon)} values")
print(f"Target times: {targ_time_vals[0]} to {targ_time_vals[-1]}, {len(targ_time_vals)} values")

# Verify these match our extracted data
print(f"\nLat shape check: {region_lat.shape}")
print(f"Lon shape check: {region_lon.shape}")
print(f"Time shape check: {targ_time_vals.shape}")
