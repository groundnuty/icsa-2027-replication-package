
import numpy as np
import datetime as dt

def day_of_year(ts):
    """Compute custom day of year: 1 Jan=1, 28 Feb=59, 29 Feb=60, 1 Mar=61, ..., 31 Dec=366."""
    d = dt.datetime.fromtimestamp(ts.astype('datetime64[ns]').astype(np.int64) / 1e9, tz=dt.timezone.utc)
    year = d.year
    month = d.month
    day = d.day
    
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
    if is_leap:
        days_in_month[1] = 29
    
    std_doy = sum(days_in_month[:month-1]) + day
    
    if not is_leap and month > 2:
        std_doy += 1
    
    return std_doy

base_data = np.load('/tmp/base_data.npy')
target_data = np.load('/tmp/target_data.npy')
base_times = np.load('/tmp/base_times.npy')
tgt_times = np.load('/tmp/tgt_times.npy')

# Compute day-of-year for all baseline and target dates
base_doy = np.array([day_of_year(t) for t in base_times])
tgt_doy = np.array([day_of_year(t) for t in tgt_times])

print("Baseline DOY range:", base_doy.min(), base_doy.max())
print("Target DOY range:", tgt_doy.min(), tgt_doy.max())

# Identify sea cells: finite SST on every day of the target period
sea_mask = np.all(np.isfinite(target_data), axis=0)
print("Sea cells count:", sea_mask.sum(), "out of", sea_mask.size)

# Save these for later
np.save('/tmp/base_doy.npy', base_doy)
np.save('/tmp/tgt_doy.npy', tgt_doy)
np.save('/tmp/sea_mask.npy', sea_mask)
