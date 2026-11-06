import h5py
import numpy as np
from datetime import datetime, timedelta

f = h5py.File('/work/sst_s2.nc', 'r')
time_raw = f['time'][:]

# Convert to dates
dates = [datetime.fromtimestamp(t) for t in time_raw]
print("First date:", dates[0])
print("Last date:", dates[-1])

# Check if dates are daily
print("Date diff first two:", dates[1] - dates[0])
print("Date diff last two:", dates[-1] - dates[-2])
