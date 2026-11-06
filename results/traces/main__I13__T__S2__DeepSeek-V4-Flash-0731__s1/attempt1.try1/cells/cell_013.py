
import numpy as np
import datetime

def date_to_doy(dates):
    """Convert dates to day-of-year index (1-366) using the specified mapping."""
    month_offsets = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335], dtype=np.int64)
    doys = np.zeros(len(dates), dtype=np.int64)
    for i, d in enumerate(dates):
        dt = np.datetime64(d, 'D').astype(datetime.datetime)
        doys[i] = month_offsets[dt.month - 1] + dt.day
    return doys

# Compute doy for extended baseline dates
base_doy = date_to_doy(base_times)
print("Base doy range:", base_doy.min(), base_doy.max())
print("Sample base doys:", base_doy[:5], "...", base_doy[-5:])

# Compute doy for target dates
target_doy = date_to_doy(target_times)
print("Target doy range:", target_doy.min(), target_doy.max())
print("Sample target doys:", target_doy[:5], "...", target_doy[-5:])
