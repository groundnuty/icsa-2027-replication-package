
import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Check the data
print("Time range:", ds.time.values[0], "to", ds.time.values[-1])
print("Lat range:", ds.latitude.values.min(), "to", ds.latitude.values.max())
print("Lon range:", ds.longitude.values.min(), "to", ds.longitude.values.max())

# Check lat/lon step
lats = ds.latitude.values
lons = ds.longitude.values
print(f"Lat step: {lats[1]-lats[0]}")
print(f"Lon step: {lons[1]-lons[0]}")

# Check region
lat_min, lat_max = 56.13, 57.33
lon_min, lon_max = 17.71, 18.91

lat_mask = (lats >= lat_min) & (lats <= lat_max)
lon_mask = (lons >= lon_min) & (lons <= lon_max)
print(f"Lat cells in region: {lat_mask.sum()}")
print(f"Lon cells in region: {lon_mask.sum()}")

# Check what the SST values look like
import numpy as np
# Take a small sample
sst_sample = ds['analysed_sst'].isel(time=0).values
print(f"SST sample shape: {sst_sample.shape}")
print(f"SST min: {np.nanmin(sst_sample)}, max: {np.nanmax(sst_sample)}")
print(f"SST mean (non-NaN): {np.nanmean(sst_sample)}")
