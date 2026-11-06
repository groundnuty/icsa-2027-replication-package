
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import xarray as xr

# ========== Load data ==========
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat_sel = ds.latitude.values
lon_sel = ds.longitude.values
lat_idx = np.where((lat_sel >= 54.13) & (lat_sel <= 55.33))[0]
lon_idx = np.where((lon_sel >= 14.67) & (lon_sel <= 15.87))[0]

base_start = np.datetime64('1991-12-27')
base_end = np.datetime64('2003-01-05')
t_idx_base = np.where((ds.time.values >= base_start) & (ds.time.values <= base_end))[0]
base_dates = ds.time.values[t_idx_base]
base_sst = ds.analysed_sst.isel(time=t_idx_base, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)

tgt_start = np.datetime64('2008-06-01')
tgt_end = np.datetime64('2008-08-31')
t_idx_tgt = np.where((ds.time.values >= tgt_start) & (ds.time.values <= tgt_end))[0]
tgt_dates = ds.time.values[t_idx_tgt]
tgt_sst = ds.analysed_sst.isel(time=t_idx_tgt, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)

base_dates_py = [datetime.utcfromtimestamp(int(d.astype('datetime64[ns]').astype(np.int64)) / 1e9) for d in base_dates]
tgt_dates_py = [datetime.utcfromtimestamp(int(d.astype('datetime64[ns]').astype(np.int64)) / 1e9) for d in tgt_dates]

# Sea cells
n_tgt = len(tgt_dates_py)
sea_cells = np.all(~np.isnan(tgt_sst), axis=0)
sea_lat_idx, sea_lon_idx = np.where(sea_cells)

# ========== Day of year mapping ==========
days_before_month = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def doy_from_date(dt):
    return days_before_month[dt.month - 1] + dt.day

# ========== Build doy -> date indices ==========
baseline_date_indices = [i for i, d in enumerate(base_dates_py) 
                         if datetime(1992,1,1) <= d <= datetime(2002,12,31)]
baseline_doy = {i: doy_from_date(base_dates_py[i]) for i in baseline_date_indices}

date_to_pools = defaultdict(list)
for i in range(len(base_dates_py)):
    t = base_dates_py[i]
    for j in baseline_date_indices:
        b = base_dates_py[j]
        if abs((t - b).days) <= 5:
            d = baseline_doy[j]
            if d != 60:
                date_to_pools[i].append(d)

doy_to_dates = defaultdict(list)
for i, pools in date_to_pools.items():
    for d in pools:
        doy_to_dates[d].append(i)

# ========== Compute threshold and climatology ==========
# Use array index = doy - 1 (0 to 365)
n_doy = 366
threshold = np.full((n_doy, 60, 60), np.nan)
climatology = np.full((n_doy, 60, 60), np.nan)

for d in range(1, n_doy+1):
    if d == 60:
        continue
    dates_in_pool = doy_to_dates[d]
    if len(dates_in_pool) == 0:
        continue
    pool_vals = base_sst[dates_in_pool, :, :]  # shape (n_dates, 60, 60)
    idx = d - 1  # 0-based index
    
    for i, (li, lo) in enumerate(zip(sea_lat_idx, sea_lon_idx)):
        vals = pool_vals[:, li, lo]
        valid = ~np.isnan(vals)
        if valid.sum() == 0:
            continue
        threshold[idx, li, lo] = np.quantile(vals[valid], 0.9, method='hazen')
        climatology[idx, li, lo] = np.mean(vals[valid])

# Set day 60 (index 59) to mean of days 59 (index 58) and 61 (index 60)
threshold[59, :, :] = (threshold[58, :, :] + threshold[60, :, :]) / 2.0
climatology[59, :, :] = (climatology[58, :, :] + climatology[60, :, :]) / 2.0

print("Threshold and climatology computed")
# Verify no NaNs in sea cells
for i, (li, lo) in enumerate(zip(sea_lat_idx, sea_lon_idx)):
    if np.any(np.isnan(threshold[:, li, lo])):
        print(f"NaN in threshold for sea cell ({li},{lo})")
        break
else:
    print("All sea cells have complete threshold arrays")

# ========== Smooth with 31-day centred moving mean wrapping ==========
def smooth_wrap(arr):
    """Smooth 366-element array with 31-day centred moving mean wrapping around."""
    n = 366
    result = np.zeros(n)
    for i in range(n):
        # Sum days i-15 to i+15 modulo n
        total = 0.0
        count = 0
        for j in range(i-15, i+16):
            k = j % n
            if not np.isnan(arr[k]):
                total += arr[k]
                count += 1
        if count > 0:
            result[i] = total / count
        else:
            result[i] = np.nan
    return result

# Apply smoothing per sea cell
for i, (li, lo) in enumerate(zip(sea_lat_idx, sea_lon_idx)):
    threshold[:, li, lo] = smooth_wrap(threshold[:, li, lo])
    climatology[:, li, lo] = smooth_wrap(climatology[:, li, lo])

print("Smoothing done")

# ========== Per-cell MHW detection ==========
# Target period: 2008-06-01 to 2008-08-31
# For each sea cell, check if each target day is hot
# day is hot if SST >= threshold[day_of_year-1, lat, lon]

# Get doy for each target day
tgt_doys = np.array([doy_from_date(d) for d in tgt_dates_py])

# Check hot days: shape (92, 60, 60)
hot = np.zeros((n_tgt, 60, 60), dtype=bool)
for i, li in enumerate(sea_lat_idx):
    for j, lo in enumerate(sea_lon_idx):
        # Get threshold for this cell at each target day
        thresh_cell = threshold[tgt_doys - 1, li, lo]
        hot[:, li, lo] = tgt_sst[:, li, lo] >= thresh_cell

print("Hot days computed. Hot days count per cell:")
print(hot.sum(axis=0).max(), "max hot days in a cell")

# Find per-cell MHWs
# A run of at least 5 consecutive hot days
# Runs separated by 1 or 2 non-hot days are joined

def find_mhw_runs(hot_days):
    """Find MHW runs in a boolean array.
    hot_days: array of length n_days (bool)
    Returns: list of (start_idx, end_idx) where the cell is in an MHW (inclusive indices)
    """
    n = len(hot_days)
    # First find hot runs
    runs = []
    i = 0
    while i < n:
        if hot_days[i]:
            start = i
            while i < n and hot_days[i]:
                i += 1
            end = i - 1
            runs.append([start, end])
        else:
            i += 1
    
    # Merge runs separated by 1 or 2 non-hot days
    if len(runs) == 0:
        return []
    
    merged = [runs[0].copy()]
    for r in runs[1:]:
        prev = merged[-1]
        gap = r[0] - prev[1] - 1
        if 1 <= gap <= 2:
            merged[-1][1] = r[1]  # join
        else:
            merged.append(r.copy())
    
    # Keep only runs of length >= 5
    mhw_runs = [(s, e) for s, e in merged if (e - s + 1) >= 5]
    return mhw_runs

# Compute per-cell MHWs
per_cell_mhw = []  # list of (lat_idx, lon_idx, [(start, end), ...])
for i, (li, lo) in enumerate(zip(sea_lat_idx, sea_lon_idx)):
    runs = find_mhw_runs(hot[:, li, lo])
    if runs:
        per_cell_mhw.append((li, lo, runs))

print(f"Cells with MHWs: {len(per_cell_mhw)} out of {len(sea_lat_idx)} sea cells")

# ========== Regional events ==========
# A day is active if at least one sea cell is inside a per-cell MHW on that day
active = np.zeros(n_tgt, dtype=bool)
for li, lo, runs in per_cell_mhw:
    for s, e in runs:
        active[s:e+1] = True

# Regional events: maximal runs of consecutive active days
events = []
i = 0
while i < n_tgt:
    if active[i]:
        start = i
        while i < n_tgt and active[i]:
            i += 1
        end = i - 1
        events.append((start, end))
    else:
        i += 1

print(f"Regional events: {len(events)}")
for s, e in events:
    print(f"  {tgt_dates_py[s].date()} to {tgt_dates_py[e].date()}")
