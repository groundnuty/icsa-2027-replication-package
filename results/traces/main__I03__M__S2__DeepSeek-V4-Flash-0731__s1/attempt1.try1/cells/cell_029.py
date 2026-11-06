
import numpy as np
from datetime import datetime, date, timedelta
import xarray as xr

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
time = ds['time'].values
target_time_idx = np.load('/tmp/target_time_idx.npy')

target_dates = []
for i in target_time_idx:
    t = time[i]
    dt = datetime.utcfromtimestamp(int(t) / 1e9)
    target_dates.append(dt.date())

# Load MHW mask
mhw_mask = np.load('/tmp/mhw_mask_correct.npy')

# Verify active days
active = mhw_mask.sum(axis=(1, 2)) > 0

# Events
events = []
in_event = False
start = 0
for i in range(len(active)):
    if active[i] and not in_event:
        start = i
        in_event = True
    elif not active[i] and in_event:
        events.append((start, i-1))
        in_event = False
if in_event:
    events.append((start, len(active)-1))

print("Regional events with dates:")
event_dates = []
for e in events:
    onset = target_dates[e[0]]
    end = target_dates[e[1]]
    event_dates.append((onset, end))
    print(f"  Event: onset={onset}, end={end}, days={e[1]-e[0]+1}")

# Check baseline analysed period
baseline_start_date = dt_date(1991, 12, 27)
baseline_end_date = dt_date(2003, 1, 5)
print(f"\nBaseline analysed: {baseline_start_date} to {baseline_end_date}")

# Target analysed period
print(f"Target analysed: {target_dates[0]} to {target_dates[-1]}")
