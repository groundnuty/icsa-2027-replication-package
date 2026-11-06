
import numpy as np
import xarray as xr
import json
import os
from datetime import datetime

# Reload everything
def doy_fixed(dt):
    month_offsets = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_offsets[dt.month - 1] + dt.day

# Load data
target_sst = np.load('/work/target_sst.npy')
target_times = np.load('/work/target_times.npy')
sea_cells = np.load('/work/sea_cells.npy')
threshold_smooth = np.load('/work/threshold_smooth.npy')
region_lats = np.load('/work/region_lats.npy')
region_lons = np.load('/work/region_lons.npy')

# Get target dates as datetime objects
target_dates = []
for t in target_times:
    dt = datetime.utcfromtimestamp(t.astype('datetime64[s]').astype(np.int64))
    target_dates.append(dt)
target_dates = np.array(target_dates)

target_doy = np.array([doy_fixed(d) for d in target_dates])

n_sea = sea_cells.sum()
target_sst_sea = target_sst[:, sea_cells]

# Compute hot mask
hot = np.zeros((len(target_dates), n_sea), dtype=bool)
for t_idx, doy in enumerate(target_doy):
    hot[t_idx, :] = target_sst_sea[t_idx, :] >= threshold_smooth[:, doy-1]

n_days, n_sea = hot.shape

# Find per-cell MHWs
cell_mhw = np.zeros_like(hot, dtype=bool)

for c in range(n_sea):
    h = hot[:, c]
    
    runs = []
    i = 0
    while i < n_days:
        if h[i]:
            start = i
            while i < n_days and h[i]:
                i += 1
            end = i - 1
            runs.append((start, end))
        else:
            i += 1
    
    if not runs:
        continue
    
    joined = [runs[0]]
    for r in runs[1:]:
        prev = joined[-1]
        gap = r[0] - prev[1] - 1
        if gap <= 2:
            joined[-1] = (prev[0], r[1])
        else:
            joined.append(r)
    
    for start, end in joined:
        if end - start + 1 >= 5:
            cell_mhw[start:end+1, c] = True

# Build full mask (92, 60, 60)
mhw_full = np.zeros((n_days, 60, 60), dtype=np.uint8)
mhw_full[:, sea_cells] = cell_mhw.astype(np.uint8)

# Regional events
active = cell_mhw.sum(axis=1) > 0
events = []
i = 0
while i < n_days:
    if active[i]:
        start = i
        while i < n_days and active[i]:
            i += 1
        end = i - 1
        events.append((start, end))
    else:
        i += 1

event_list = []
for s, e in events:
    event_list.append({
        "onset": target_dates[s].strftime('%Y-%m-%d'),
        "end": target_dates[e].strftime('%Y-%m-%d')
    })

# Create output directory
os.makedirs('output', exist_ok=True)

# Create xarray Dataset for mhw_mask.nc
# Coordinates: time (target days), lat (region lat), lon (region lon)
time_coords = np.array([np.datetime64(t.isoformat()) for t in target_dates])
lat_coords = region_lats.astype(np.float32)
lon_coords = region_lons.astype(np.float32)

ds = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_full)
    },
    coords={
        'time': time_coords,
        'lat': lat_coords,
        'lon': lon_coords
    }
)

# Set mhw as uint8
ds['mhw'] = ds['mhw'].astype('uint8')

# Write NetCDF
ds.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Wrote output/mhw_mask.nc")
print("Dimensions:", ds['mhw'].shape)
print("Time range:", ds['time'].values[0], "to", ds['time'].values[-1])

# Write report.json
report = {
    "region": {
        "lat_min": 63.31,
        "lat_max": 64.51,
        "lon_min": 21.31,
        "lon_max": 22.51
    },
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": "2009-06-01",
        "end": "2009-08-31"
    },
    "events": event_list,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print("Wrote output/report.json")
print(json.dumps(report, indent=2))
