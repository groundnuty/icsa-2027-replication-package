
import numpy as np
import datetime

# Load data
sst_base = np.load('sst_base.npy')
sst_target = np.load('sst_target.npy')
base_times_int = np.load('base_times.npy')
target_times_int = np.load('target_times.npy')
lat_vals = np.load('lat_vals.npy')
lon_vals = np.load('lon_vals.npy')
base_times = base_times_int.astype('datetime64[D]')
target_times = target_times_int.astype('datetime64[D]')

# Recompute thresholds for verification
def date_to_doy(dates):
    month_offsets = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335], dtype=np.int64)
    doys = np.zeros(len(dates), dtype=np.int64)
    for i, d in enumerate(dates):
        dt = np.datetime64(d, 'D').astype(datetime.datetime)
        doys[i] = month_offsets[dt.month - 1] + dt.day
    return doys

# Rebuild pool indices (need this for verification)
bl_start_idx = 5
bl_end_idx = 4022
baseline_dates = base_times[bl_start_idx:bl_end_idx+1]
baseline_doy = date_to_doy(baseline_dates)

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

# Recompute raw thresholds
n_lat, n_lon = 60, 60
thresholds_raw = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
for d in range(1, 367):
    if d == 60:
        continue
    idx = pool_indices[d]
    pool = sst_base[idx, :, :]
    thresholds_raw[d-1] = np.nanpercentile(pool, 90, axis=0, method='hazen')

thresholds_raw[59] = (thresholds_raw[58] + thresholds_raw[60]) / 2.0

# Verify the raw threshold for a specific cell and doy
# Cell (0,0), doy 153 (index 152)
print("=== Verification: threshold for cell (0,0), doy 153 ===")
pool_153 = sst_base[pool_indices[153], 0, 0]
print(f"Pool size: {len(pool_153)}")
print(f"Pool values (first 10): {pool_153[:10]}")
print(f"Pool NaN count: {np.isnan(pool_153).sum()}")
print(f"Manual percentile (hazen): {np.percentile(pool_153, 90, method='hazen')}")
print(f"Automated threshold: {thresholds_raw[152, 0, 0]}")
print(f"Match: {np.isclose(np.percentile(pool_153, 90, method='hazen'), thresholds_raw[152, 0, 0])}")

# Verify the pool contains the expected dates
print(f"\nPool dates for doy 153 (first 5 and last 5):")
for i in [0, 1, 2, 3, 4, -5, -4, -3, -2, -1]:
    idx = pool_indices[153][i]
    print(f"  {base_times[idx]}")

# Verify doy 153 is June 1
print(f"\nTarget doy 153: {target_times[0]} has doy {date_to_doy([target_times[0]])[0]}")

# Verify sea cells
sea_cells = np.all(np.isfinite(sst_target), axis=0)
print(f"\nSea cells: {sea_cells.sum()}")
