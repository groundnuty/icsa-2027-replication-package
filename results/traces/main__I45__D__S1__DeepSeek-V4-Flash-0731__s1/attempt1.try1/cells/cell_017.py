
import numpy as np
from datetime import datetime, timedelta

# Load saved data
base_sst = np.load('/work/base_sst.npy')  # (4028, 60, 60)
target_sst = np.load('/work/target_sst.npy')  # (92, 60, 60)
region_lats = np.load('/work/region_lats.npy')
region_lons = np.load('/work/region_lons.npy')
base_times = np.load('/work/base_times.npy')
target_times = np.load('/work/target_times.npy')

# Convert base_times to datetime
base_dates = []
for t in base_times:
    dt = datetime.utcfromtimestamp(t.astype('datetime64[s]').astype(np.int64))
    base_dates.append(dt)
base_dates = np.array(base_dates)

print("First base date:", base_dates[0])
print("Last base date:", base_dates[-1])

# Function to compute day of year (1-366, leap-year mapping)
def doy_fixed(dt):
    month_offsets = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_offsets[dt.month - 1] + dt.day

# Check the day-of-year for some dates
print("1992-01-01 doy:", doy_fixed(datetime(1992,1,1)))
print("1992-02-28 doy:", doy_fixed(datetime(1992,2,28)))
print("1992-02-29 doy:", doy_fixed(datetime(1992,2,29)))
print("1992-03-01 doy:", doy_fixed(datetime(1992,3,1)))
print("1993-03-01 doy:", doy_fixed(datetime(1993,3,1)))  # non-leap, still 61
print("1992-06-01 doy:", doy_fixed(datetime(1992,6,1)))
print("1992-08-31 doy:", doy_fixed(datetime(1992,8,31)))
