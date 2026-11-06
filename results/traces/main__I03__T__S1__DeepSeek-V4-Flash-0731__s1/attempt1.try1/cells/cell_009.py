
import fsspec
import xarray as xr
import numpy as np
import datetime

fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Get lat and lon indices
lat_mask = (ds.latitude >= 54.17) & (ds.latitude <= 55.37)
lon_mask = (ds.longitude >= 13.25) & (ds.longitude <= 14.45)
lat_idx = np.where(lat_mask.values)[0]
lon_idx = np.where(lon_mask.values)[0]
print(f"lat_idx: {lat_idx[0]} to {lat_idx[-1]}, count={len(lat_idx)}")
print(f"lon_idx: {lon_idx[0]} to {lon_idx[-1]}, count={len(lon_idx)}")

# Load baseline region data
baseline_start = np.datetime64('1991-12-27')
baseline_end = np.datetime64('2003-01-05')
baseline_mask = (ds.time.values >= baseline_start) & (ds.time.values <= baseline_end)
baseline_indices = np.where(baseline_mask)[0]

# Load target region data
target_start = np.datetime64('2014-06-01')
target_end = np.datetime64('2014-08-31')
target_mask = (ds.time.values >= target_start) & (ds.time.values <= target_end)
target_indices = np.where(target_mask)[0]

# Load the region subset
print("Loading baseline data...")
baseline_data = ds['analysed_sst'].isel(time=baseline_indices, latitude=lat_idx, longitude=lon_idx)
print("Baseline data shape:", baseline_data.shape)
baseline_vals = baseline_data.values
print("Baseline loaded, dtype:", baseline_vals.dtype)

print("Loading target data...")
target_data = ds['analysed_sst'].isel(time=target_indices, latitude=lat_idx, longitude=lon_idx)
print("Target data shape:", target_data.shape)
target_vals = target_data.values
print("Target loaded, dtype:", target_vals.dtype)

# Save the data
np.save('baseline_vals.npy', baseline_vals)
np.save('target_vals.npy', target_vals)
np.save('baseline_dates.npy', ds.time.values[baseline_indices].astype('datetime64[D]').astype(str))
np.save('target_dates.npy', ds.time.values[target_indices].astype('datetime64[D]').astype(str))
np.save('lat_vals.npy', ds.latitude.values[lat_idx])
np.save('lon_vals.npy', ds.longitude.values[lon_idx])

print("Data saved.")
