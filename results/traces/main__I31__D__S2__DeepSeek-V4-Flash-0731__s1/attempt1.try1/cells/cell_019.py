
import numpy as np
import pandas as pd
import xarray as xr

# Load data
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
thresholds_smooth = np.load('/work/thresholds_smooth.npy')  # (366, 60, 60)
sea_cells = np.load('/work/sea_cells.npy')  # (60, 60)

target_data = ds['analysed_sst'].isel(time=slice(12935, 13027), latitude=slice(260, 320), longitude=slice(485, 545)).load()
target_times = target_data.time.values
target_data64 = target_data.values.astype(np.float64)  # (92, 60, 60)

# Get the first sea cell
sea_indices = np.where(sea_cells)
i, j = sea_indices[0][0], sea_indices[1][0]
print(f"Sea cell at lat_idx={i}, lon_idx={j}")
print(f"Latitude: {ds.latitude.values[260+i]}, Longitude: {ds.longitude.values[485+j]}")

# Check SST for June-August 2017 at this cell
print("\nSST values at this cell:")
for t in range(0, 92, 7):
    dt = pd.Timestamp(target_times[t])
    print(f"  {dt.date()}: SST={target_data64[t, i, j]:.2f} K, DOY={dt.timetuple().tm_yday}, threshold={thresholds_smooth[dt.timetuple().tm_yday - 1, i, j]:.2f} K")

# Check the raw (unsmoothed) threshold
# We need to reload the raw thresholds
# Actually, let me check the pool directly

# Load baseline data for the cell
base_data = ds['analysed_sst'].isel(time=slice(3647, 7675), latitude=slice(260, 320), longitude=slice(485, 545)).load()
base_times = base_data.time.values
base_data64 = base_data.values.astype(np.float64)

# Day of year function
def doy_from_datetime64(t):
    dt = pd.Timestamp(t).to_pydatetime()
    year = dt.year
    month = dt.month
    day = dt.day
    is_leap = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if is_leap:
        days_in_month[1] = 29
    std_doy = sum(days_in_month[:month-1]) + day
    if not is_leap and month >= 3:
        return std_doy + 1
    else:
        return std_doy

base_doy = np.array([doy_from_datetime64(t) for t in base_times])
in_baseline = (base_times >= np.datetime64('1992-01-01')) & (base_times <= np.datetime64('2002-12-31'))

# Pool for DOY=153 (June 1)
d = 153
baseline_indices = np.where(in_baseline & (base_doy == d))[0]
print(f"\nBaseline dates with DOY={d}:")
for bi in baseline_indices:
    print(f"  {pd.Timestamp(base_times[bi]).date()}")

# Build pool mask
pool_mask = np.zeros(len(base_times), dtype=bool)
for bi in baseline_indices:
    lo = max(0, bi - 5)
    hi = min(len(base_times) - 1, bi + 5)
    pool_mask[lo:hi+1] = True

pool_idx = np.where(pool_mask)[0]
print(f"\nPool indices count: {len(pool_idx)}")
print("Pool dates:")
for pi in pool_idx:
    dt = pd.Timestamp(base_times[pi])
    print(f"  {dt.date()}")

# Get pool values for the cell
pool_values = base_data64[pool_mask, i, j]
print(f"\nPool values for cell ({i},{j}):")
print(f"  Finite values: {np.isfinite(pool_values).sum()} out of {len(pool_values)}")
print(f"  Non-NaN values: {pool_values[np.isfinite(pool_values)]}")
print(f"  Range: [{np.nanmin(pool_values):.2f}, {np.nanmax(pool_values):.2f}]")
print(f"  Mean: {np.nanmean(pool_values):.2f}")
print(f"  90th percentile (hazen): {np.nanpercentile(pool_values, 90, method='hazen'):.2f}")
