
import numpy as np
import pandas as pd

# Load saved data
thresholds_smooth = np.load('/work/thresholds_smooth.npy')  # (366, 60, 60)
sea_cells = np.load('/work/sea_cells.npy')  # (60, 60)

# Load target data
import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
target_data = ds['analysed_sst'].isel(time=slice(12935, 13027), latitude=slice(260, 320), longitude=slice(485, 545)).load()
target_times = target_data.time.values
target_data64 = target_data.values.astype(np.float64)  # (92, 60, 60)

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

target_doy = np.array([doy_from_datetime64(t) for t in target_times])

# For each target day, get the threshold for each cell
threshold_for_target = thresholds_smooth[target_doy - 1, :, :]  # (92, 60, 60)

# Check values for a few sea cells
sea_indices = np.where(sea_cells)
print("First few sea cells:")
for idx in range(min(5, len(sea_indices[0]))):
    i, j = sea_indices[0][idx], sea_indices[1][idx]
    sst = target_data64[:, i, j]
    thresh = threshold_for_target[:, i, j]
    print(f"  Cell ({i},{j}): SST range [{np.nanmin(sst):.2f}, {np.nanmax(sst):.2f}], Threshold range [{np.nanmin(thresh):.2f}, {np.nanmax(thresh):.2f}]")
    hot_days = sst >= thresh
    print(f"    Hot days: {hot_days.sum()}")
    # Check runs
    runs = []
    start = None
    for t in range(len(hot_days)):
        if hot_days[t]:
            if start is None:
                start = t
        else:
            if start is not None:
                runs.append((start, t-1))
                start = None
    if start is not None:
        runs.append((start, len(hot_days)-1))
    print(f"    Runs: {runs}")
    for s, e in runs:
        print(f"      Run: {pd.Timestamp(target_times[s]).date()} to {pd.Timestamp(target_times[e]).date()}, length={e-s+1}")
