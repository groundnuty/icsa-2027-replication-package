
import numpy as np
import datetime as dt
import xarray as xr
import json

# ============================================================
# Step 0: Load data for region
# ============================================================
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Region indices
lat_min_idx, lat_max_idx = 34, 93
lon_min_idx, lon_max_idx = 213, 272

# All time data for the region
times = ds.time.values
lats = ds.latitude.values[lat_min_idx:lat_max_idx+1]
lons = ds.longitude.values[lon_min_idx:lon_max_idx+1]

# Convert numpy datetime64 to Python dates for processing
dates = [dt.datetime.utcfromtimestamp(t.astype('datetime64[us]').astype(np.int64) / 1e6) for t in times]

# Let's verify
print(f"First date: {dates[0]}, Last date: {dates[-1]}")
print(f"Lat range: {lats[0]} to {lats[-1]}, count: {len(lats)}")
print(f"Lon range: {lons[0]} to {lons[-1]}, count: {len(lons)}")
