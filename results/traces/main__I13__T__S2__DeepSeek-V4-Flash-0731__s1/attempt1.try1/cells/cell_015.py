
import numpy as np
import datetime

# Load saved data
sst_base = np.load('sst_base.npy')
sst_target = np.load('sst_target.npy')
base_times_int = np.load('base_times.npy')
target_times_int = np.load('target_times.npy')
base_times = base_times_int.astype('datetime64[D]')
target_times = target_times_int.astype('datetime64[D]')

print("Base SST shape:", sst_base.shape)
print("Target SST shape:", sst_target.shape)
print("Base times:", base_times[0], "to", base_times[-1], "count:", len(base_times))
print("Target times:", target_times[0], "to", target_times[-1], "count:", len(target_times))

def date_to_doy(dates):
    """Convert dates to day-of-year index (1-366) using the specified mapping."""
    month_offsets = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335], dtype=np.int64)
    doys = np.zeros(len(dates), dtype=np.int64)
    for i, d in enumerate(dates):
        dt = np.datetime64(d, 'D').astype(datetime.datetime)
        doys[i] = month_offsets[dt.month - 1] + dt.day
    return doys

base_doy = date_to_doy(base_times)
target_doy = date_to_doy(target_times)
print("Base doy range:", base_doy.min(), base_doy.max())
print("Target doy range:", target_doy.min(), target_doy.max())
print("Target doy values:", target_doy)
