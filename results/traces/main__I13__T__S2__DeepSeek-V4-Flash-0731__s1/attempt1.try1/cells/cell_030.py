
import numpy as np
import datetime
import json
import os

# Create output directory
os.makedirs('output', exist_ok=True)

# ============================================================
# STEP 1: Load saved data
# ============================================================
sst_base = np.load('sst_base.npy')          # (4028, 60, 60) float64 - extended baseline
sst_target = np.load('sst_target.npy')      # (92, 60, 60) float64 - target period
base_times_int = np.load('base_times.npy')  # int64 datetime values
target_times_int = np.load('target_times.npy')
lat_vals = np.load('lat_vals.npy')          # (60,) float32
lon_vals = np.load('lon_vals.npy')          # (60,) float32

base_times = base_times_int.astype('datetime64[D]')
target_times = target_times_int.astype('datetime64[D]')

print("Loaded data:")
print(f"  sst_base: {sst_base.shape}, sst_target: {sst_target.shape}")
print(f"  base_times: {base_times[0]} to {base_times[-1]}")
print(f"  target_times: {target_times[0]} to {target_times[-1]}")
print(f"  lat: {lat_vals[0]} to {lat_vals[-1]}, count: {len(lat_vals)}")
print(f"  lon: {lon_vals[0]} to {lon_vals[-1]}, count: {len(lon_vals)}")

# ============================================================
# STEP 2: Day-of-year mapping
# ============================================================
def date_to_doy(dates):
    """Convert dates to day-of-year index (1-366) by month and day.
    1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366.
    Month offsets: Jan=0, Feb=31, Mar=60, Apr=91, May=121, Jun=152,
    Jul=182, Aug=213, Sep=244, Oct=274, Nov=305, Dec=335.
    """
    month_offsets = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335], dtype=np.int64)
    doys = np.zeros(len(dates), dtype=np.int64)
    for i, d in enumerate(dates):
        dt = np.datetime64(d, 'D').astype(datetime.datetime)
        doys[i] = month_offsets[dt.month - 1] + dt.day
    return doys

base_doy = date_to_doy(base_times)
target_doy = date_to_doy(target_times)
print(f"\nDay-of-year mapping computed. Base doy range: {base_doy.min()}-{base_doy.max()}")
print(f"Target doy range: {target_doy.min()}-{target_doy.max()}")

# ============================================================
# STEP 3: Identify baseline period indices
# ============================================================
bl_start_idx = 5  # 1992-01-01
bl_end_idx = 4022  # 2002-12-31
baseline_dates = base_times[bl_start_idx:bl_end_idx+1]
baseline_doy = date_to_doy(baseline_dates)
print(f"\nBaseline: {baseline_dates[0]} to {baseline_dates[-1]}, {len(baseline_dates)} days")

# ============================================================
# STEP 4: Build pool indices for each day of year
# ============================================================
pool_indices = {}
for d in range(1, 367):
    if d == 60:
        continue
    bl_where = np.where(baseline_doy == d)[0]
    bl_abs_idx = bl_where + bl_start_idx
    all_indices = set()
    for bi in bl_abs_idx:
        B = base_times[bi]
        lo = B - np.timedelta64(5, 'D')
        hi = B + np.timedelta64(5, 'D')
        t_lo = np.searchsorted(base_times, lo)
        t_hi = np.searchsorted(base_times, hi, side='right')
        all_indices.update(range(t_lo, t_hi))
    pool_indices[d] = sorted(all_indices)

print(f"\nPool indices built for {len(pool_indices)} doys")
print(f"Sample pool sizes: doy 1: {len(pool_indices[1])}, doy 153: {len(pool_indices[153])}, doy 366: {len(pool_indices[366])}")

# ============================================================
# STEP 5: Compute thresholds and climatologies
# ============================================================
print("\nComputing thresholds and climatologies...")
n_lat, n_lon = 60, 60
thresholds = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
climatologies = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)

for d in range(1, 367):
    if d == 60:
        continue
    idx = pool_indices[d]
    pool = sst_base[idx, :, :]  # (N_pool, 60, 60)
    thresholds[d-1] = np.nanpercentile(pool, 90, axis=0, method='hazen')
    climatologies[d-1] = np.nanmean(pool, axis=0)

# Set day 60 (index 59) to mean of days 59 and 61 (indices 58 and 60)
thresholds[59] = (thresholds[58] + thresholds[60]) / 2.0
climatologies[59] = (climatologies[58] + climatologies[60]) / 2.0

print(f"Raw thresholds: NaN count = {np.isnan(thresholds).sum()}")
print(f"Raw climatologies: NaN count = {np.isnan(climatologies).sum()}")

# ============================================================
# STEP 6: Smooth with centred 31-day moving mean (wrap-around)
# ============================================================
def smooth_wrap(arr):
    """Apply centred 31-day moving mean wrapping around a 366-element array along axis 0."""
    n = 366
    padded = np.concatenate([arr[-15:], arr, arr[:15]], axis=0)  # (396, 60, 60)
    result = np.zeros((n, 60, 60), dtype=np.float64)
    for i in range(n):
        result[i] = np.mean(padded[i:i+31], axis=0)
    return result

print("Smoothing thresholds and climatologies...")
thresholds_smooth = smooth_wrap(thresholds)
climatologies_smooth = smooth_wrap(climatologies)

print(f"Smoothed thresholds: NaN count = {np.isnan(thresholds_smooth).sum()}")
print(f"Smoothed climatologies: NaN count = {np.isnan(climatologies_smooth).sum()}")

# Verify smoothing: day 1 (index 0) should be mean of days 1-16 and 352-366
# (indices 0-15 and 351-365)
expected = np.mean(np.concatenate([thresholds[351:366], thresholds[0:16]]), axis=0)
actual = thresholds_smooth[0]
print(f"Smoothing check (day 1): max diff = {np.max(np.abs(expected - actual)):.2e}")

# Verify day 366 (index 365) wraps correctly
expected = np.mean(np.concatenate([thresholds[350:366], thresholds[0:15]]), axis=0)
actual = thresholds_smooth[365]
print(f"Smoothing check (day 366): max diff = {np.max(np.abs(expected - actual)):.2e}")

# ============================================================
# STEP 7: Identify sea cells
# ============================================================
sea_cells = np.all(np.isfinite(sst_target), axis=0)  # (60, 60)
n_sea = sea_cells.sum()
print(f"\nSea cells: {n_sea} out of {60*60}")

# ============================================================
# STEP 8: Per-cell MHW detection
# ============================================================
print("\nComputing per-cell MHWs...")

# For each target day, get the threshold for each cell
thresholds_for_target = np.zeros_like(sst_target)  # (92, 60, 60)
for t in range(len(target_doy)):
    thresholds_for_target[t] = thresholds_smooth[target_doy[t] - 1]

# Hot days: SST >= threshold (only for sea cells)
hot = sst_target >= thresholds_for_target
hot = hot & sea_cells[np.newaxis, :, :]

print(f"Hot cell-days: {hot.sum()} out of {92 * n_sea}")

# Find per-cell MHWs
def find_mhws(hot):
    """Find per-cell MHWs from a boolean array of hot days.
    Returns list of (start_idx, end_idx) inclusive.
    """
    n = len(hot)
    runs = []
    i = 0
    while i < n:
        if hot[i]:
            j = i
            while j < n and hot[j]:
                j += 1
            runs.append((i, j-1))
            i = j
        else:
            i += 1
    
    mhws = [(s, e) for s, e in runs if e - s + 1 >= 5]
    
    if len(mhws) <= 1:
        return mhws
    
    joined = [mhws[0]]
    for s, e in mhws[1:]:
        prev_s, prev_e = joined[-1]
        gap = s - prev_e - 1
        if gap <= 2:
            joined[-1] = (prev_s, e)
        else:
            joined.append((s, e))
    
    return joined

# Create mhw_mask (time, lat, lon) as uint8
mhw_mask = np.zeros((len(target_times), 60, 60), dtype=np.uint8)

# Store per-cell MHWs for verification
n_cells_with_mhw = 0
n_total_mhws = 0

for lat_i in range(60):
    for lon_i in range(60):
        if sea_cells[lat_i, lon_i]:
            hot_cell = hot[:, lat_i, lon_i]
            mhws = find_mhws(hot_cell)
            if len(mhws) > 0:
                n_cells_with_mhw += 1
            n_total_mhws += len(mhws)
            for s, e in mhws:
                mhw_mask[s:e+1, lat_i, lon_i] = 1

print(f"Cells with at least one MHW: {n_cells_with_mhw} out of {n_sea}")
print(f"Total per-cell MHWs: {n_total_mhws}")
print(f"MHW mask sum: {mhw_mask.sum()}")

# ============================================================
# STEP 9: Regional events
# ============================================================
print("\nComputing regional events...")

# A day is active if at least one sea cell is inside a per-cell MHW
active = np.any(mhw_mask > 0, axis=(1, 2))  # (92,)

# Find maximal runs of consecutive active days
runs = []
i = 0
n = len(active)
while i < n:
    if active[i]:
        j = i
        while j < n and active[j]:
            j += 1
        runs.append((i, j-1))
        i = j
    else:
        i += 1

events = []
for s, e in runs:
    onset = np.datetime_as_string(target_times[s], unit='D')
    end = np.datetime_as_string(target_times[e], unit='D')
    events.append({"onset": onset, "end": end})
    print(f"  Event: {onset} to {end} ({e-s+1} active days)")

if len(events) == 0:
    print("  No regional events")

# ============================================================
# STEP 10: Write output files
# ============================================================
print("\nWriting output files...")

# Write mhw_mask.nc
import xarray as xr

ds_out = xr.Dataset(
    {
        "mhw": (("time", "lat", "lon"), mhw_mask)
    },
    coords={
        "time": target_times,
        "lat": lat_vals,
        "lon": lon_vals,
    }
)
ds_out.mhw.attrs['description'] = '1 where cell is inside a per-cell MHW, 0 otherwise'
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("  Wrote output/mhw_mask.nc")

# Write report.json
report = {
    "region": {
        "lat_min": 56.09,
        "lat_max": 57.29,
        "lon_min": 10.55,
        "lon_max": 11.75
    },
    "baseline_analysed": {
        "start": "1992-01-01",
        "end": "2002-12-31"
    },
    "target_analysed": {
        "start": "2021-06-01",
        "end": "2021-08-31"
    },
    "events": events,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print("  Wrote output/report.json")

print("\nDone!")
