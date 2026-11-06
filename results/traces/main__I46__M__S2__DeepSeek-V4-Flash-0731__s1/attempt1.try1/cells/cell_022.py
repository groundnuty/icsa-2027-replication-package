
import xarray as xr
import numpy as np
import json
import os
from datetime import date, timedelta

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

time = ds.time.values
lat = ds.latitude.values
lon = ds.longitude.values
lat_idx = np.where((lat >= 64.39) & (lat <= 65.59))[0]
lon_idx = np.where((lon >= 23.41) & (lon <= 24.61))[0]

region_lat = lat[lat_idx]
region_lon = lon[lon_idx]

target_start = np.datetime64('2013-06-01')
target_end = np.datetime64('2013-08-31')
target_mask = (time >= target_start) & (time <= target_end)
target_time_idx = np.where(target_mask)[0]
target_time = time[target_time_idx]

n_target = len(target_time_idx)
n_lat = len(lat_idx)
n_lon = len(lon_idx)

print("n_target:", n_target, "n_lat:", n_lat, "n_lon:", n_lon)

# Load the hot array and sea_mask
hot = np.load('/tmp/hot.npy')
sea_mask = np.load('/tmp/sea_mask.npy')
print("hot shape:", hot.shape, "sea_mask shape:", sea_mask.shape)
print("hot dtype:", hot.dtype, "sea_mask dtype:", sea_mask.dtype)

# Now find per-cell MHWs
mhw_mask = np.zeros_like(hot, dtype=bool)

for li in range(n_lat):
    for loni in range(n_lon):
        if not sea_mask[li, loni]:
            continue
        
        hot_seq = hot[:, li, loni]
        
        # Find runs of hot days
        runs = []
        i = 0
        while i < n_target:
            if hot_seq[i]:
                j = i
                while j < n_target and hot_seq[j]:
                    j += 1
                runs.append((i, j - 1))
                i = j
            else:
                i += 1
        
        # Filter runs with length >= 5
        long_runs = [(s, e) for s, e in runs if e - s + 1 >= 5]
        
        if len(long_runs) == 0:
            continue
        
        # Join runs separated by 1-2 non-hot days
        joined_runs = [long_runs[0]]
        for s, e in long_runs[1:]:
            prev_s, prev_e = joined_runs[-1]
            gap = s - prev_e - 1
            if 1 <= gap <= 2:
                joined_runs[-1] = (prev_s, e)
            else:
                joined_runs.append((s, e))
        
        # Mark MHW days
        for s, e in joined_runs:
            mhw_mask[s:e+1, li, loni] = True

print("Per-cell MHW mask computed")
print("Total MHW cell-days:", mhw_mask.sum())
print("Cells in MHW at some point:", mhw_mask.any(axis=0).sum())

# Regional events
active = mhw_mask.any(axis=(1, 2))
print("Active days:", active.sum())

events = []
i = 0
while i < n_target:
    if active[i]:
        j = i
        while j < n_target and active[j]:
            j += 1
        events.append((i, j - 1))
        i = j
    else:
        i += 1

print("Regional events:", len(events))
for s, e in events:
    print(f"  Event: target day {s} to {e} ({e - s + 1} days)")

# Convert to dates
def npdt_to_date(t):
    dt = t.astype('datetime64[D]').astype(object)
    return date(dt.year, dt.month, dt.day)

event_list = []
for s, e in events:
    start_date = npdt_to_date(target_time[s])
    end_date = npdt_to_date(target_time[e])
    event_list.append({
        "onset": start_date.isoformat(),
        "end": end_date.isoformat()
    })
    print(f"  Event: {start_date} to {end_date}")

# Save mhw_mask
np.save('/tmp/mhw_mask.npy', mhw_mask)
print("Saved mhw_mask")
