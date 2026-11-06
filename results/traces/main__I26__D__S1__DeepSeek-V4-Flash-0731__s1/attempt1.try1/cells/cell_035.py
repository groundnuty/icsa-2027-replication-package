import numpy as np
from datetime import datetime, timedelta

# Load smoothed threshold and climatology
threshold_smooth = np.load('/work/threshold_smooth.npy')  # (60, 60, 366)
climatology_smooth = np.load('/work/climatology_smooth.npy')

# Load target data
target_data = np.load('/work/target_data.npy').astype(np.float64)

# Day-of-year mapping
def day_of_year(month, day):
    month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:month-1]) + day

# Target dates: 2007-06-01 to 2007-08-31
target_dates = []
d = datetime(2007, 6, 1)
end = datetime(2007, 8, 31)
while d <= end:
    target_dates.append(d)
    d += timedelta(days=1)

print(f"Target dates: {len(target_dates)}")
print(f"First: {target_dates[0]}, Last: {target_dates[-1]}")

# Compute day-of-year for each target date
target_doy = np.array([day_of_year(dt.month, dt.day) for dt in target_dates])
print("Target DOYs:", target_doy)

# For each sea cell, check if hot on each target day
# sea_mask = finite on all target days
sea_mask = np.all(~np.isnan(target_data), axis=0)
print(f"Sea cells: {np.sum(sea_mask)}")

# Initialize hot mask: (92, 60, 60)
hot = np.zeros((92, 60, 60), dtype=bool)

# For each target day t, check SST >= threshold for that day-of-year
for t in range(92):
    doy = target_doy[t]
    # threshold_smooth[:, :, doy-1] is the threshold for this day-of-year
    hot[t] = (target_data[t] >= threshold_smooth[:, :, doy-1]) & sea_mask

print(f"Hot cells on day 0 (Jun 1): {np.sum(hot[0])}")
print(f"Hot cells on day 45: {np.sum(hot[45])}")
print(f"Hot cells on day 91 (Aug 31): {np.sum(hot[91])}")
