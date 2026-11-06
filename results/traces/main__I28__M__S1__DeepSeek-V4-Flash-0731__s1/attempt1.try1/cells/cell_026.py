
import numpy as np
import xarray as xr
import json
import os
import warnings
from datetime import date, timedelta

warnings.filterwarnings('ignore')

def doy_of_date(d):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[d.month-1] + d.day

# Load intermediate results
threshold = np.load('/tmp/threshold.npy')
climatology = np.load('/tmp/climatology.npy')
region_lat = np.load('/tmp/region_lat.npy')
region_lon = np.load('/tmp/region_lon.npy')
sea_mask = np.load('/tmp/sea_mask.npy')
target_dates_str = np.load('/tmp/target_dates_str.npy', allow_pickle=True)
target_sst = np.load('/tmp/target_sst.npy')

nlat, nlon = region_lat.shape[0], region_lon.shape[0]
n_target = target_sst.shape[0]
target_dates = [date.fromisoformat(d) for d in target_dates_str]
print(f"Loaded: threshold {threshold.shape}, target {target_sst.shape}")
print(f"Sea cells: {sea_mask.sum()}, n_target: {n_target}")

# ====== Smoothing ======
def smooth_31(a):
    n = 366
    result = np.full_like(a, np.nan)
    for i in range(n):
        idxs = [(i + k) % n for k in range(-15, 16)]
        result[i] = np.nanmean(a[idxs], axis=0)
    return result

threshold_smooth = smooth_31(threshold)
climatology_smooth = smooth_31(climatology)
print("Smoothed threshold and climatology")

# Verify smoothing for sea cells
sea_indices = np.where(sea_mask)
# Check that all sea cells have valid smoothed threshold for all doys
all_valid = True
for ilat, ilon in zip(sea_indices[0], sea_indices[1]):
    if np.any(np.isnan(threshold_smooth[:, ilat, ilon])):
        all_valid = False
        print(f"Cell ({ilat},{ilon}) has NaN smoothed threshold")
        break
print(f"All sea cells have valid smoothed thresholds: {all_valid}")

# ====== Per-cell MHW detection ======
target_doy_idx = np.array([doy_of_date(d) - 1 for d in target_dates])  # 0-indexed
print(f"Target doy indices: {target_doy_idx[0]} to {target_doy_idx[-1]}")

mhw_mask = np.zeros((n_target, nlat, nlon), dtype=np.uint8)
n_sea = len(sea_indices[0])

for idx in range(n_sea):
    ilat = sea_indices[0][idx]
    ilon = sea_indices[1][idx]
    
    sst_cell = target_sst[:, ilat, ilon]
    thr_cell = threshold_smooth[target_doy_idx, ilat, ilon]
    
    hot = sst_cell >= thr_cell
    
    # Find maximal runs of True
    runs = []
    i = 0
    while i < n_target:
        if hot[i]:
            start = i
            while i < n_target and hot[i]:
                i += 1
            runs.append((start, i-1))
        else:
            i += 1
    
    # Filter to runs >= 5
    mhws = [r for r in runs if r[1] - r[0] + 1 >= 5]
    
    # Join MHWs separated by 1-2 non-hot days
    changed = True
    while changed:
        changed = False
        new_mhws = []
        i = 0
        while i < len(mhws):
            if i + 1 < len(mhws):
                gap = mhws[i+1][0] - mhws[i][1] - 1
                if 1 <= gap <= 2:
                    new_mhws.append((mhws[i][0], mhws[i+1][1]))
                    i += 2
                    changed = True
                    continue
            new_mhws.append(mhws[i])
            i += 1
        mhws = new_mhws
    
    # Set mhw mask
    for (start, end) in mhws:
        mhw_mask[start:end+1, ilat, ilon] = 1

# Count cells with MHWs
cells_with_mhw = np.sum(np.any(mhw_mask, axis=0) & sea_mask)
print(f"Cells with at least one MHW: {cells_with_mhw} out of {n_sea} sea cells")
print(f"Total hot cell-days in MHWs: {np.sum(mhw_mask)}")

# ====== Regional events ======
active = np.any(mhw_mask, axis=(1, 2))  # (n_target,)
print(f"Active days: {np.sum(active)} out of {n_target}")

events = []
i = 0
while i < n_target:
    if active[i]:
        start = i
        while i < n_target and active[i]:
            i += 1
        events.append({
            'onset': target_dates[start].strftime('%Y-%m-%d'),
            'end': target_dates[i-1].strftime('%Y-%m-%d')
        })
    else:
        i += 1

print(f"Regional events: {len(events)}")
for ev in events:
    print(f"  {ev['onset']} to {ev['end']}")

# ====== Write output files ======
os.makedirs('output', exist_ok=True)

# Create mhw_mask.nc
time_coords = np.array([np.datetime64(d.isoformat()) for d in target_dates])
ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_mask)
    },
    coords={
        'time': time_coords,
        'lat': region_lat,
        'lon': region_lon
    }
)
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("mhw_mask.nc written")

# Create report.json
report = {
    'region': {
        'lat_min': 57.85,
        'lat_max': 59.05,
        'lon_min': 21.01,
        'lon_max': 22.21
    },
    'baseline_analysed': {
        'start': '1991-12-27',
        'end': '2003-01-05'
    },
    'target_analysed': {
        'start': '2013-06-01',
        'end': '2013-08-31'
    },
    'events': events,
    'complete': True,
    'caveats': ''
}
with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print("report.json written")

# Verify output files
print("\nOutput files:")
print("mhw_mask.nc exists:", os.path.exists('output/mhw_mask.nc'))
print("report.json exists:", os.path.exists('output/report.json'))

# Print report content
with open('output/report.json', 'r') as f:
    print(f.read())
