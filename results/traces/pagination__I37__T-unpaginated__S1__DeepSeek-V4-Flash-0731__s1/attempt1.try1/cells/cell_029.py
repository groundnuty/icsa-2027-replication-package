
import numpy as np
import datetime
import pickle
import os
import json
import xarray as xr
import fsspec

# =============================================
# Load all saved data
# =============================================
baseline_sst = np.load('work/baseline_sst.npy')
with open('work/baseline_dates.pkl', 'rb') as f:
    baseline_dates = pickle.load(f)
with open('work/date_to_idx.pkl', 'rb') as f:
    date_to_idx = pickle.load(f)
with open('work/doy_to_pool_dates.pkl', 'rb') as f:
    doy_to_pool_dates = pickle.load(f)
doy_to_pool_dates = {k: set(v) for k, v in doy_to_pool_dates.items()}

threshold = np.load('work/threshold.npy')
climatology = np.load('work/climatology.npy')
threshold_smooth = np.load('work/threshold_smooth.npy')
climatology_smooth = np.load('work/climatology_smooth.npy')
target_sst = np.load('work/target_sst.npy')
sea_mask = np.load('work/sea_mask.npy')

# =============================================
# Region info
# =============================================
lat_min, lat_max = 60.09, 61.29
lon_min, lon_max = 20.01, 21.21

# Get region lat/lon from dataset
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
f = fs.open(f'{base}/sst_20120601.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
lats_all = ds.latitude.values
lons_all = ds.longitude.values
lat_idx_arr = np.where((lats_all >= lat_min) & (lats_all <= lat_max))[0]
lon_idx_arr = np.where((lons_all >= lon_min) & (lons_all <= lon_max))[0]
region_lats = lats_all[lat_idx_arr]
region_lons = lons_all[lon_idx_arr]
ds.close()
f.close()

print(f"Region: {len(lat_idx_arr)}x{len(lon_idx_arr)} cells")
print(f"Lat range: {region_lats[0]:.4f} to {region_lats[-1]:.4f}")
print(f"Lon range: {region_lons[0]:.4f} to {region_lons[-1]:.4f}")

# =============================================
# Target dates
# =============================================
target_start = datetime.date(2012, 6, 1)
target_end = datetime.date(2012, 8, 31)
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += datetime.timedelta(days=1)

n_target = len(target_dates)
n_lat = len(lat_idx_arr)
n_lon = len(lon_idx_arr)

# Day of year mapping
def doy_from_date(date):
    month_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_days[date.month-1] + date.day

target_doy = np.array([doy_from_date(date) for date in target_dates])

print(f"Target dates: {n_target} days, from {target_dates[0]} to {target_dates[-1]}")
print(f"Target DOY range: {target_doy[0]} to {target_doy[-1]}")

# =============================================
# Verify threshold/climatology for target days
# =============================================
# Reshape threshold and climatology
threshold_3d = threshold_smooth.reshape(366, n_lat, n_lon)
climatology_3d = climatology_smooth.reshape(366, n_lat, n_lon)

# Get thresholds for target days
threshold_target = threshold_3d[target_doy - 1]  # (92, 60, 60)
climatology_target = climatology_3d[target_doy - 1]

# Check for NaN in threshold for sea cells
sea_threshold_nan = np.isnan(threshold_target).any(axis=0)
print(f"Sea cells with NaN in target thresholds: {(sea_threshold_nan & sea_mask).sum()}")

# =============================================
# Compute hot days
# =============================================
hot = (target_sst >= threshold_target) & sea_mask[np.newaxis, :, :]
print(f"Hot cell-days: {hot.sum()}")
print(f"Sea cells: {sea_mask.sum()}")

# =============================================
# Compute per-cell MHWs
# =============================================
cell_mhw = np.zeros((n_target, n_lat, n_lon), dtype=np.uint8)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_mask[i, j]:
            continue
        hot_days = hot[:, i, j]
        
        # Find maximal runs of consecutive hot days
        runs = []
        in_run = False
        run_start = 0
        for t in range(n_target):
            if hot_days[t]:
                if not in_run:
                    in_run = True
                    run_start = t
            else:
                if in_run:
                    runs.append((run_start, t - 1))
                    in_run = False
        if in_run:
            runs.append((run_start, n_target - 1))
        
        if len(runs) == 0:
            continue
        
        # Join runs separated by 1-2 non-hot days
        joined_runs = []
        current = list(runs[0])
        for next_run in runs[1:]:
            gap = next_run[0] - current[1] - 1
            if gap <= 2:
                current[1] = next_run[1]
            else:
                joined_runs.append(tuple(current))
                current = list(next_run)
        joined_runs.append(tuple(current))
        
        # Filter runs of length >= 5
        for run_start, run_end in joined_runs:
            if run_end - run_start + 1 >= 5:
                cell_mhw[run_start:run_end+1, i, j] = 1

print(f"Cells with MHWs: {(cell_mhw.any(axis=0)).sum()}")
print(f"Total cell-MHW days: {cell_mhw.sum()}")

# =============================================
# Compute regional events
# =============================================
# A day is active if at least one sea cell is inside a per-cell MHW on that day
active_days = cell_mhw.any(axis=(1, 2))  # (92,)
print(f"Active days: {active_days.sum()}")

# Find regional events (maximal runs of consecutive active days)
events = []
in_event = False
event_start = 0
for t in range(n_target):
    if active_days[t]:
        if not in_event:
            in_event = True
            event_start = t
    else:
        if in_event:
            events.append((event_start, t - 1))
            in_event = False
if in_event:
    events.append((event_start, n_target - 1))

print(f"Regional events: {len(events)}")

event_list = []
for start, end in events:
    event_list.append({
        "onset": target_dates[start].isoformat(),
        "end": target_dates[end].isoformat()
    })
    print(f"  Event: {target_dates[start]} to {target_dates[end]}")

# =============================================
# Write output files
# =============================================
os.makedirs('output', exist_ok=True)

# Write mhw_mask.nc
time_coords = np.array([np.datetime64(date.isoformat()) for date in target_dates], dtype='datetime64[ns]')
lat_coords = region_lats
lon_coords = region_lons

ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), cell_mhw.astype(np.uint8))
    },
    coords={
        'time': time_coords,
        'lat': lat_coords,
        'lon': lon_coords
    }
)
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Wrote output/mhw_mask.nc")

# Write report.json
report = {
    "region": {
        "lat_min": lat_min,
        "lat_max": lat_max,
        "lon_min": lon_min,
        "lon_max": lon_max
    },
    "baseline_analysed": {
        "start": baseline_dates[0].isoformat(),
        "end": baseline_dates[-1].isoformat()
    },
    "target_analysed": {
        "start": target_dates[0].isoformat(),
        "end": target_dates[-1].isoformat()
    },
    "events": event_list,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Wrote output/report.json")
print(json.dumps(report, indent=2))
