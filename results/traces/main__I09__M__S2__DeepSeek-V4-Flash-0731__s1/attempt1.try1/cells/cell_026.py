
import os
import json
import numpy as np
import pandas as pd
import xarray as xr

# Create output directory
os.makedirs('output', exist_ok=True)

# ============================================
# Load all saved data
# ============================================
sst_data = np.load('/tmp/sst_data.npy')
time_int = np.load('/tmp/time_sub.npy')
time_sub = time_int.astype('datetime64[s]')
lat_vals = np.load('/tmp/lat_vals.npy')
lon_vals = np.load('/tmp/lon_vals.npy')
sea_mask = np.load('/tmp/sea_mask.npy')
thresholds_smoothed = np.load('/tmp/thresholds_smoothed.npy')
climatology_smoothed = np.load('/tmp/climatology_smoothed.npy')
mhw_cell = np.load('/tmp/mhw_cell.npy')

# ============================================
# Define DOY function
# ============================================
def date_to_doy(date):
    ts = pd.Timestamp(date)
    month, day = ts.month, ts.day
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month-1] + day

# ============================================
# Target period
# ============================================
target_start = np.datetime64('2022-06-01')
target_end = np.datetime64('2022-08-31')
target_mask = (time_sub >= target_start) & (time_sub <= target_end)
target_idx = np.where(target_mask)[0]
target_dates = pd.to_datetime(time_sub[target_idx])
n_target = len(target_idx)
print(f"Target days: {n_target}")

# Target period dates as strings
target_date_strs = [d.strftime('%Y-%m-%d') for d in target_dates]

# ============================================
# Regional events from mhw_cell
# ============================================
active = mhw_cell.any(axis=(1, 2))  # (n_target,)

# Find maximal runs of consecutive active days
events = []
i = 0
while i < len(active):
    if active[i]:
        j = i
        while j < len(active) and active[j]:
            j += 1
        onset = target_date_strs[i]
        end = target_date_strs[j-1]
        events.append({"onset": onset, "end": end})
        i = j
    else:
        i += 1

print(f"Regional events: {len(events)}")
for e in events:
    print(f"  {e['onset']} to {e['end']}")

# ============================================
# Create mhw_mask.nc
# ============================================
# mhw_cell has shape (92, 60, 60) boolean
# Convert to uint8: 1 where in MHW, 0 otherwise
mhw_uint8 = mhw_cell.astype(np.uint8)

# Create xarray Dataset
time_coords = target_dates.values  # datetime64 array
lat_coords = lat_vals
lon_coords = lon_vals

ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_uint8)
    },
    coords={
        'time': time_coords,
        'lat': lat_coords,
        'lon': lon_coords,
    }
)

# Write netCDF
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Wrote output/mhw_mask.nc")

# ============================================
# Create report.json
# ============================================
report = {
    "region": {
        "lat_min": 54.81,
        "lat_max": 56.01,
        "lon_min": 19.61,
        "lon_max": 20.81
    },
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": "2022-06-01",
        "end": "2022-08-31"
    },
    "events": events,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print("Wrote output/report.json")

# Verify output files
print("\n--- Verification ---")
print("report.json content:")
with open('output/report.json', 'r') as f:
    print(f.read())
