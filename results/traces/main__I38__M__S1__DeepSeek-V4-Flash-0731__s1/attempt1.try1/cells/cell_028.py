
import numpy as np
import xarray as xr
from datetime import date, timedelta
import json, time, os

intermediate_dir = 'intermediate'
output_dir = 'output'
os.makedirs(output_dir, exist_ok=True)

# ===== Load metadata =====
with open(f'{intermediate_dir}/metadata.json') as f:
    meta = json.load(f)

baseline_dates = [date.fromisoformat(d) for d in meta['baseline_dates']]
target_dates = [date.fromisoformat(d) for d in meta['target_dates']]
region_lats = np.load(f'{intermediate_dir}/region_lats.npy')
region_lons = np.load(f'{intermediate_dir}/region_lons.npy')

# ===== Load data =====
threshold_smooth = np.load(f'{intermediate_dir}/threshold_smooth.npy')
climatology_smooth = np.load(f'{intermediate_dir}/climatology_smooth.npy')
sea_cells = np.load(f'{intermediate_dir}/sea_cells.npy')
target_sst = np.load(f'{intermediate_dir}/target_sst.npy')

print(f"threshold_smooth: {threshold_smooth.shape}")
print(f"target_sst: {target_sst.shape}")
print(f"sea_cells: {sea_cells.sum()} sea cells")

# ===== Day of year mapping =====
def day_of_year(d):
    month_days = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:d.month]) + d.day

target_doy = [day_of_year(d) for d in target_dates]
n_days = len(target_dates)
n_lat, n_lon = 60, 60

# ===== Compute hot days =====
# A day is hot if SST >= threshold for that day of year
hot = np.zeros((n_days, n_lat, n_lon), dtype=bool)
for i in range(n_days):
    doy = target_doy[i]
    sst = target_sst[i].astype(np.float64)
    th = threshold_smooth[doy - 1]
    hot[i] = (sst >= th) & ~np.isnan(sst)

print(f"Hot days: {hot.sum()}")

# ===== Per-cell MHW detection (Interpretation B) =====
# 1. A per-cell MHW is a run of >= 5 consecutive hot days
# 2. Per-cell MHWs separated by 1-2 non-hot days are joined
# 3. Gap days belong to the joined MHW

mhw_mask = np.zeros((n_days, n_lat, n_lon), dtype=np.uint8)

t0 = time.time()
for la in range(n_lat):
    for lo in range(n_lon):
        if not sea_cells[la, lo]:
            continue
        
        cell_hot = hot[:, la, lo]
        
        # Find runs of hot days
        runs = []
        i = 0
        while i < n_days:
            if cell_hot[i]:
                start = i
                while i < n_days and cell_hot[i]:
                    i += 1
                end = i - 1
                runs.append((start, end))
            else:
                i += 1
        
        # Identify MHWs as runs of >= 5 hot days
        mhws = [(s, e) for s, e in runs if e - s + 1 >= 5]
        
        # Join MHWs separated by 1-2 cold days
        if mhws:
            merged = [mhws[0]]
            for m in mhws[1:]:
                gap = m[0] - merged[-1][1] - 1
                if gap <= 2:
                    merged[-1] = (merged[-1][0], m[1])
                else:
                    merged.append(m)
            
            # Mark merged MHWs (including gap days)
            for start, end in merged:
                mhw_mask[start:end+1, la, lo] = 1

print(f"MHW mask computation took {time.time()-t0:.1f}s")
print(f"MHW mask sum: {mhw_mask.sum()}")

# ===== Regional events =====
# A day is active if at least one sea cell is in a per-cell MHW
active = mhw_mask.any(axis=(1, 2))
print(f"Active days: {active.sum()}")

# Find maximal runs of consecutive active days
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

print(f"Regional events: {len(events)}")
event_list = []
for s, e in events:
    onset = target_dates[s].isoformat()
    end = target_dates[e].isoformat()
    print(f"  Event: {onset} to {end}")
    event_list.append({"onset": onset, "end": end})

# ===== Write output files =====

# Write mhw_mask.nc
# Create xarray dataset with time, lat, lon dimensions
time_coords = np.array(target_dates, dtype='datetime64[ns]')
lat_coords = region_lats.astype(np.float32)
lon_coords = region_lons.astype(np.float32)

ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_mask.astype(np.uint8))
    },
    coords={
        'time': time_coords,
        'lat': lat_coords,
        'lon': lon_coords,
    }
)

ds_out.to_netcdf(f'{output_dir}/mhw_mask.nc', engine='h5netcdf')
print(f"mhw_mask.nc written")

# Write report.json
report = {
    'region': {
        'lat_min': float(region_lats[0]),
        'lat_max': float(region_lats[-1]),
        'lon_min': float(region_lons[0]),
        'lon_max': float(region_lons[-1]),
    },
    'baseline_analysed': {
        'start': baseline_dates[0].isoformat(),
        'end': baseline_dates[-1].isoformat(),
    },
    'target_analysed': {
        'start': target_dates[0].isoformat(),
        'end': target_dates[-1].isoformat(),
    },
    'events': event_list,
    'complete': True,
    'caveats': '',
}

with open(f'{output_dir}/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print(f"report.json written")
print(f"Done!")
