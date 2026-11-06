
import numpy as np
import pickle
import datetime
import json
import os
import fsspec
import xarray as xr

# ============================================================
# 1. Load data
# ============================================================
print("Loading data...")

# Load float64 thresholds
threshold_smooth = np.load('/tmp/threshold_smooth_v2.npy')  # float64, (366, 60, 60)
climatology_smooth = np.load('/tmp/climatology_smooth_v2.npy')  # float64, (366, 60, 60)

# Load target SST and convert to float64
target_sst = np.load('/tmp/target_sst.npy').astype(np.float64)  # (92, 60, 60) float64

# Load sea cell mask
sea_cells = np.load('/tmp/sea_cells.npy')  # (60, 60) bool

print(f"Threshold shape: {threshold_smooth.shape}, dtype: {threshold_smooth.dtype}")
print(f"Target SST shape: {target_sst.shape}, dtype: {target_sst.dtype}")
print(f"Sea cells: {sea_cells.sum()}")

# ============================================================
# 2. Compute target dates and doys
# ============================================================
target_dates = []
d = datetime.date(2021, 6, 1)
while d <= datetime.date(2021, 8, 31):
    target_dates.append(d)
    d += datetime.timedelta(days=1)
n_days = len(target_dates)

def doy_from_date(date):
    month_starts = [1, 32, 61, 92, 122, 153, 183, 214, 245, 275, 306, 336]
    return month_starts[date.month - 1] + date.day - 1

target_doys = [doy_from_date(d) for d in target_dates]
print(f"Target days: {n_days}")

# ============================================================
# 3. Compute hot days
# ============================================================
print("\nComputing hot days...")

# For each sea cell and target day, check if hot (SST >= threshold)
sea_idx = np.where(sea_cells)
n_sea = len(sea_idx[0])

hot = np.zeros((n_days, 60, 60), dtype=bool)

for si in range(n_sea):
    li, loi = sea_idx[0][si], sea_idx[1][si]
    for i in range(n_days):
        d = target_doys[i] - 1  # 0-based index into threshold array
        sst_val = target_sst[i, li, loi]
        thr_val = threshold_smooth[d, li, loi]
        # Comparison in float64; NaN threshold gives False (not hot)
        if not np.isnan(sst_val) and not np.isnan(thr_val):
            hot[i, li, loi] = sst_val >= thr_val

print(f"Hot day count: {hot.sum()}")

# ============================================================
# 4. Find per-cell MHWs
# ============================================================
print("\nFinding per-cell MHWs...")

def find_per_cell_mhws(hot_array):
    """Find per-cell MHWs from a boolean array of hot days."""
    n = len(hot_array)
    # Find all maximal runs of hot days
    runs = []
    i = 0
    while i < n:
        if hot_array[i]:
            j = i
            while j < n and hot_array[j]:
                j += 1
            runs.append((i, j-1))
            i = j
        else:
            i += 1
    
    # Keep runs with length >= 5
    mhws = [(s, e) for s, e in runs if e - s + 1 >= 5]
    
    # Merge MHWs separated by 1-2 non-hot days
    merged = []
    for mhw in mhws:
        if not merged:
            merged.append(mhw)
        else:
            prev_end = merged[-1][1]
            gap = mhw[0] - prev_end - 1
            if 1 <= gap <= 2:
                merged[-1] = (merged[-1][0], mhw[1])
            else:
                merged.append(mhw)
    
    return merged

# mhw_mask: (n_days, 60, 60) uint8 - 1 if cell is inside a per-cell MHW on that day
mhw_mask = np.zeros((n_days, 60, 60), dtype=np.uint8)

for si in range(n_sea):
    li, loi = sea_idx[0][si], sea_idx[1][si]
    cell_hot = hot[:, li, loi]
    mhws = find_per_cell_mhws(cell_hot)
    for (s, e) in mhws:
        mhw_mask[s:e+1, li, loi] = 1

print(f"MHW mask sum: {mhw_mask.sum()}")
print(f"Cells with MHWs: {(mhw_mask.max(axis=0) > 0).sum()}")

# ============================================================
# 5. Find regional events
# ============================================================
print("\nFinding regional events...")

# A day is active if at least one sea cell is inside a per-cell MHW on that day
active = mhw_mask.max(axis=(1, 2)) > 0
print(f"Active days: {active.sum()}")

# Find maximal runs of consecutive active days
regional_events = []
i = 0
while i < n_days:
    if active[i]:
        j = i
        while j < n_days and active[j]:
            j += 1
        regional_events.append((i, j-1))
        i = j
    else:
        i += 1

print(f"Regional events: {len(regional_events)}")
events_list = []
for s, e in regional_events:
    onset = target_dates[s].strftime('%Y-%m-%d')
    end = target_dates[e].strftime('%Y-%m-%d')
    events_list.append({"onset": onset, "end": end})
    print(f"  Event: {onset} to {end} ({e-s+1} days)")

# ============================================================
# 6. Generate output files
# ============================================================
print("\nGenerating output files...")

# Create output directory
os.makedirs('output', exist_ok=True)

# Get coordinate values
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
lat_start, lat_end = 48, 108
lon_start, lon_end = 353, 413

with fs.open(f'{base}/sst_20210601.nc', 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    region_lats = ds.latitude.values[lat_start:lat_end]
    region_lons = ds.longitude.values[lon_start:lon_end]

# Create time coordinate
time_values = np.array([np.datetime64(d) for d in target_dates])

# Create xarray dataset for mhw_mask
ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_mask)
    },
    coords={
        'time': time_values,
        'lat': region_lats,
        'lon': region_lons
    }
)

# Write to NetCDF
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print(f"Wrote output/mhw_mask.nc")
print(f"  mhw dtype: {ds_out.mhw.dtype}")
print(f"  mhw shape: {ds_out.mhw.shape}")

# Write report.json
report = {
    "region": {
        "lat_min": 54.45,
        "lat_max": 55.65,
        "lon_min": 16.05,
        "lon_max": 17.25
    },
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": "2021-06-01",
        "end": "2021-08-31"
    },
    "events": events_list,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print("Wrote output/report.json")
print(json.dumps(report, indent=2))

print("\nDone!")
