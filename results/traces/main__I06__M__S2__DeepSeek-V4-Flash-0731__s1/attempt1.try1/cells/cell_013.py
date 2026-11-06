
import xarray as xr
import numpy as np
import pandas as pd
import os

os.makedirs('output', exist_ok=True)

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

t = ds.time.values
lat = ds.latitude.values
lon = ds.longitude.values

# Region indices
lat_sel = (lat >= 54.45) & (lat <= 55.65)
lon_sel = (lon >= 16.05) & (lon <= 17.25)
lat_idx = np.where(lat_sel)[0]
lon_idx = np.where(lon_sel)[0]
print(f"Lat indices: {lat_idx[0]}..{lat_idx[-1]}, n={len(lat_idx)}")
print(f"Lon indices: {lon_idx[0]}..{lon_idx[-1]}, n={len(lon_idx)}")

# Time indices
start_baseline = np.datetime64('1991-12-27')
end_baseline = np.datetime64('2003-01-05')
mask_baseline = (t >= start_baseline) & (t <= end_baseline)
baseline_idx = np.where(mask_baseline)[0]

start_target = np.datetime64('2012-06-01')
end_target = np.datetime64('2012-08-31')
mask_target = (t >= start_target) & (t <= end_target)
target_idx = np.where(mask_target)[0]

print(f"Baseline indices: {baseline_idx[0]}..{baseline_idx[-1]}, n={len(baseline_idx)}")
print(f"Target indices: {target_idx[0]}..{target_idx[-1]}, n={len(target_idx)}")

# Load baseline data for region
sst_baseline = ds.analysed_sst.isel(time=baseline_idx, latitude=lat_idx, longitude=lon_idx).values
print(f"Baseline data shape: {sst_baseline.shape}, dtype={sst_baseline.dtype}")

# Load target data for region
sst_target = ds.analysed_sst.isel(time=target_idx, latitude=lat_idx, longitude=lon_idx).values
print(f"Target data shape: {sst_target.shape}, dtype={sst_target.dtype}")

# Determine sea cells
sea_cells = ~np.isnan(sst_target).any(axis=0)
print(f"Sea cells: {sea_cells.sum()}")

# Save
np.save('/tmp/sst_baseline.npy', sst_baseline)
np.save('/tmp/sst_target.npy', sst_target)
np.save('/tmp/sea_cells.npy', sea_cells)

baseline_dates = t[baseline_idx]
target_dates = t[target_idx]
np.save('/tmp/baseline_dates.npy', baseline_dates)
np.save('/tmp/target_dates.npy', target_dates)

# Save lat/lon coords for the region
np.save('/tmp/region_lat.npy', lat[lat_idx])
np.save('/tmp/region_lon.npy', lon[lon_idx])
print("Saved intermediate data")
