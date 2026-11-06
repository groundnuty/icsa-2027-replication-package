# ============================================================
# Detect per-cell MHWs in target period
# ============================================================
# For each sea cell and target day, determine if hot (SST >= threshold)

# Get day-of-year for each target date
target_doy = np.array([date_to_doy(d) for d in target_dates])
print("Target day-of-years:", target_doy)

# Check the day-of-year mapping
for i, d in enumerate(target_dates):
    doy = date_to_doy(d)
    print(f"  {d}: doy={doy}")
    if i > 5:
        break

# Determine hot days per cell
# hot[li, loi, t] = True if target_data[t, li, loi] >= thresholds[target_doy[t]-1, li, loi]
hot = np.zeros((n_lat, n_lon, n_target_days), dtype=bool)

for t in range(n_target_days):
    doy = target_doy[t]
    idx = doy - 1
    hot[:, :, t] = (target_data[t, :, :] >= thresholds[idx, :, :]) & sea_cells

print(f"Hot days: {hot.sum()} out of {sea_cells.sum() * n_target_days}")

# ============================================================
# Find per-cell MHWs
# A per-cell MHW is a run of >= 5 consecutive hot days.
# Per-cell MHWs separated by 1 or 2 non-hot days are joined into one.
# ============================================================
# For each sea cell, find MHW segments in the target period
# Returns a boolean array mhw_mask[t, li, loi] indicating if cell is in a per-cell MHW on day t

mhw_mask = np.zeros((n_target_days, n_lat, n_lon), dtype=bool)

for li in range(n_lat):
    for loi in range(n_lon):
        if not sea_cells[li, loi]:
            continue
        
        # Get hot days for this cell
        hot_days = hot[li, loi, :]  # boolean array of length n_target_days
        
        # Find runs of hot days
        # A run of hot days is a maximal consecutive sequence of True values
        
        # First, identify hot runs
        runs = []
        in_run = False
        run_start = 0
        for t in range(n_target_days):
            if hot_days[t]:
                if not in_run:
                    run_start = t
                    in_run = True
            else:
                if in_run:
                    runs.append((run_start, t - 1))
                    in_run = False
        if in_run:
            runs.append((run_start, n_target_days - 1))
        
        if not runs:
            continue
        
        # Filter runs of length >= 5
        mhw_runs = [(s, e) for s, e in runs if (e - s + 1) >= 5]
        
        if not mhw_runs:
            continue
        
        # Join runs separated by 1 or 2 non-hot days
        joined_runs = []
        current = list(mhw_runs[0])
        for i in range(1, len(mhw_runs)):
            prev_end = current[1]
            next_start = mhw_runs[i][0]
            gap = next_start - prev_end - 1
            if gap <= 2:
                # Join
                current[1] = mhw_runs[i][1]
            else:
                joined_runs.append(tuple(current))
                current = list(mhw_runs[i])
        joined_runs.append(tuple(current))
        
        # Mark days in per-cell MHWs
        for s, e in joined_runs:
            mhw_mask[s:e+1, li, loi] = True

print(f"Per-cell MHW mask days: {mhw_mask.sum()}")

# ============================================================
# Compute regional events
# ============================================================
# A day is active if at least one sea cell is inside a per-cell MHW on that day
active = np.any(mhw_mask, axis=(1, 2))  # boolean of length n_target_days
print(f"Active days: {active.sum()}")

# Regional MHW events are maximal runs of consecutive active days
events = []
in_event = False
event_start = 0
for t in range(n_target_days):
    if active[t]:
        if not in_event:
            event_start = t
            in_event = True
    else:
        if in_event:
            events.append((event_start, t - 1))
            in_event = False
if in_event:
    events.append((event_start, n_target_days - 1))

print(f"Regional events: {len(events)}")
for s, e in events:
    print(f"  {target_dates[s]} to {target_dates[e]}")

# ============================================================
# Write output files
# ============================================================
# Create output directory
os.makedirs('output', exist_ok=True)

# Write mhw_mask.nc
# mhw has dimensions (time, lat, lon) covering the target days
target_time = time[target_start_idx:target_end_idx+1]

# Create dataset for output
mhw_da = xr.DataArray(
    mhw_mask.astype(np.uint8),
    dims=['time', 'lat', 'lon'],
    coords={
        'time': target_time,
        'lat': lat_region,
        'lon': lon_region
    },
    name='mhw'
)

mhw_ds = mhw_da.to_dataset()
mhw_ds.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Wrote output/mhw_mask.nc")

# Write report.json
report = {
    'region': {
        'lat_min': 60.49,
        'lat_max': 61.69,
        'lon_min': 17.25,
        'lon_max': 18.45
    },
    'baseline_analysed': {
        'start': '1991-12-27',
        'end': '2003-01-05'
    },
    'target_analysed': {
        'start': '2003-06-01',
        'end': '2003-08-31'
    },
    'events': [
        {'onset': target_dates[s].strftime('%Y-%m-%d'),
         'end': target_dates[e].strftime('%Y-%m-%d')}
        for s, e in events
    ],
    'complete': True,
    'caveats': ''
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Wrote output/report.json")
print(json.dumps(report, indent=2))
