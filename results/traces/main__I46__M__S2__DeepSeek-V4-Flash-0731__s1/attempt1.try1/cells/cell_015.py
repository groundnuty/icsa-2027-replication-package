
import xarray as xr
import numpy as np

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

time = ds.time.values
lat = ds.latitude.values
lon = ds.longitude.values
lat_idx = np.where((lat >= 64.39) & (lat <= 65.59))[0]
lon_idx = np.where((lon >= 23.41) & (lon <= 24.61))[0]

# Load target data to check sea cells
target_start = np.datetime64('2013-06-01')
target_end = np.datetime64('2013-08-31')
target_mask = (time >= target_start) & (time <= target_end)
target_time_idx = np.where(target_mask)[0]
target_data = ds.analysed_sst.isel(time=target_time_idx, latitude=lat_idx, longitude=lon_idx).values

sea_mask = ~np.isnan(target_data).any(axis=0)

# Check against threshold validity
threshold_raw = np.load('/tmp/threshold_raw.npy')
valid_threshold = ~np.isnan(threshold_raw[0, :, :])  # all cells that have valid threshold for day 1

print("Sea cells:", sea_mask.sum())
print("Valid threshold cells:", valid_threshold.sum())
print("Same:", np.array_equal(sea_mask, valid_threshold))

# Check if all sea cells have valid thresholds for all days
for doy in [1, 59, 61, 182, 366]:
    valid_doy = ~np.isnan(threshold_raw[doy-1, :, :])
    print(f"Day {doy}: valid cells {valid_doy.sum()}, sea cells {sea_mask.sum()}, match: {np.array_equal(valid_doy, sea_mask)}")
