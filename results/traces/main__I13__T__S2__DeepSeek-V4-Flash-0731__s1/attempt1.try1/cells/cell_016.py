
import numpy as np

# Load saved data
base_times_int = np.load('base_times.npy')
base_times = base_times_int.astype('datetime64[D]')

# Find baseline period indices (1992-01-01 to 2002-12-31)
bl_start = np.datetime64('1992-01-01')
bl_end = np.datetime64('2002-12-31')
bl_start_idx = np.searchsorted(base_times, bl_start)
bl_end_idx = np.searchsorted(base_times, bl_end, side='right') - 1
print("Baseline indices in extended array:", bl_start_idx, bl_end_idx)
print("Baseline dates:", base_times[bl_start_idx], "to", base_times[bl_end_idx])
print("Number of baseline days:", bl_end_idx - bl_start_idx + 1)

# These are baseline dates
baseline_dates = base_times[bl_start_idx:bl_end_idx+1]

# Compute doy for baseline dates
import datetime

def date_to_doy(dates):
    month_offsets = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335], dtype=np.int64)
    doys = np.zeros(len(dates), dtype=np.int64)
    for i, d in enumerate(dates):
        dt = np.datetime64(d, 'D').astype(datetime.datetime)
        doys[i] = month_offsets[dt.month - 1] + dt.day
    return doys

baseline_doy = date_to_doy(baseline_dates)
print("Baseline doy values (first 10):", baseline_doy[:10])
print("Baseline doy values (last 10):", baseline_doy[-10:])
print("Unique doy values:", np.unique(baseline_doy))
print("Count of unique doys:", len(np.unique(baseline_doy)))
