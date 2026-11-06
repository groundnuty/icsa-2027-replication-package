
import numpy as np
import xarray as xr
from datetime import date, timedelta
import json

def doy_of_date(d):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[d.month-1] + d.day

# Load output
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds['mhw'].values
time_coords = ds['time'].values
lat_coords = ds['lat'].values
lon_coords = ds['lon'].values
ds.close()

# Load intermediate results
threshold = np.load('/tmp/threshold.npy')
target_sst = np.load('/tmp/target_sst.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

# Recompute smoothing
def smooth_31(a):
    n = 366
    result = np.full_like(a, np.nan)
    for i in range(n):
        idxs = [(i + k) % n for k in range(-15, 16)]
        result[i] = np.nanmean(a[idxs], axis=0)
    return result

threshold_smooth = smooth_31(threshold)

# Target dates and doy indices
target_dates = [date.fromisoformat(d) for d in np.load('/tmp/target_dates_str.npy', allow_pickle=True)]
target_doy_idx = np.array([doy_of_date(d) - 1 for d in target_dates])

# Verify: all non-sea cells have mhw = 0
non_sea = ~sea_mask
print("Non-sea cells with mhw=1:", np.sum(mhw[:, non_sea]))
print("All non-sea cells have mhw=0:", np.all(mhw[:, non_sea] == 0))

# Verify: all sea cells have mhw=0 or mhw=1
print("Sea cells with mhw>1:", np.sum(mhw[:, sea_mask] > 1))
print("mhw values are only 0 or 1:", np.all((mhw[:, sea_mask] == 0) | (mhw[:, sea_mask] == 1)))

# Manually compute per-cell MHWs for a few sample cells and compare
def find_mhw_runs(hot):
    n = len(hot)
    runs = []
    i = 0
    while i < n:
        if hot[i]:
            start = i
            while i < n and hot[i]:
                i += 1
            runs.append((start, i-1))
        else:
            i += 1
    mhws = [r for r in runs if r[1] - r[0] + 1 >= 5]
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
    return mhws

# Pick a few sea cells to verify
sea_indices = np.where(sea_mask)
sample_cells = [(sea_indices[0][0], sea_indices[1][0]),  # First sea cell
                (sea_indices[0][100], sea_indices[1][100]),  # 101st sea cell
                (sea_indices[0][500], sea_indices[1][500]),  # 501st sea cell
                (sea_indices[0][1500], sea_indices[1][1500]),  # 1501st sea cell
                (sea_indices[0][3000], sea_indices[1][3000])]  # 3001st sea cell

for ilat, ilon in sample_cells:
    sst_cell = target_sst[:, ilat, ilon]
    thr_cell = threshold_smooth[target_doy_idx, ilat, ilon]
    hot = sst_cell >= thr_cell
    mhws = find_mhw_runs(hot)
    
    # Check against mhw_mask
    expected = np.zeros(92, dtype=np.uint8)
    for (start, end) in mhws:
        expected[start:end+1] = 1
    
    actual = mhw[:, ilat, ilon]
    match = np.array_equal(expected, actual)
    print(f"Cell ({ilat},{ilon}): MHW runs={mhws}, match={match}")

# Verify regional events
active = np.any(mhw, axis=(1,2))
events = []
i = 0
while i < len(active):
    if active[i]:
        start = i
        while i < len(active) and active[i]:
            i += 1
        events.append({
            'onset': np.datetime_as_string(time_coords[start], unit='D'),
            'end': np.datetime_as_string(time_coords[i-1], unit='D')
        })
    else:
        i += 1

print("\nRegional events from mhw_mask:")
for ev in events:
    print(f"  {ev['onset']} to {ev['end']}")

# Load report and compare
with open('output/report.json', 'r') as f:
    report = json.load(f)

print("\nReport events:")
for ev in report['events']:
    print(f"  {ev['onset']} to {ev['end']}")

# Check if they match
report_events = [(ev['onset'], ev['end']) for ev in report['events']]
mask_events = [(ev['onset'], ev['end']) for ev in events]
print(f"\nEvents match: {report_events == mask_events}")

# Verify report fields
print("\nReport fields check:")
print(f"  region: {report['region']}")
print(f"  baseline_analysed: {report['baseline_analysed']}")
print(f"  target_analysed: {report['target_analysed']}")
print(f"  complete: {report['complete']}")
print(f"  caveats: '{report['caveats']}'")
