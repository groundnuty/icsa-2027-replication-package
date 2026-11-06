
import numpy as np
import pandas as pd

# Load saved data
thresholds_smooth = np.load('/work/thresholds_smooth.npy')
climatology_smooth = np.load('/work/climatology_smooth.npy')
sea_cells = np.load('/work/sea_cells.npy')
target_times = np.load('/work/target_times.npy', allow_pickle=True)

print("Thresholds shape:", thresholds_smooth.shape)
print("Sea cells shape:", sea_cells.shape)
print("Target times:", target_times[0], "to", target_times[-1])
print("Target days:", len(target_times))

# Compute day of year for target dates
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
print("Target DOY values:", target_doy)
print("Target dates with their DOY:")
for i, (t, d) in enumerate(zip(target_times, target_doy)):
    print(f"  {pd.Timestamp(t).date()}: DOY={d}")
