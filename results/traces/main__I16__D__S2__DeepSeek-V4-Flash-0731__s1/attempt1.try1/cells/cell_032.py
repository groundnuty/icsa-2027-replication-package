
import numpy as np

mhw_mask = np.load('/work/mhw_mask.npy')

# Active days: at least one cell is in an MHW
active = np.any(mhw_mask, axis=(1, 2))  # (92,)
print("Active days:", np.where(active)[0])

# Find maximal runs of active days
n_t = len(active)
events = []
i = 0
while i < n_t:
    if active[i]:
        start = i
        while i < n_t and active[i]:
            i += 1
        events.append((start, i-1))
    else:
        i += 1

print("Number of regional events:", len(events))
for e in events:
    print(f"  Event: days {e[0]} to {e[1]} (inclusive)")

# Convert to dates
from datetime import date, timedelta
import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
time = ds.time.values
t_start = np.where(time >= np.datetime64('2008-06-01'))[0][0]
t_end = np.where(time <= np.datetime64('2008-08-31'))[0][-1]
target_times = time[t_start:t_end+1]

for e in events:
    onset = str(target_times[e[0]])[:10]
    end = str(target_times[e[1]])[:10]
    print(f"  Onset: {onset}, End: {end}")
