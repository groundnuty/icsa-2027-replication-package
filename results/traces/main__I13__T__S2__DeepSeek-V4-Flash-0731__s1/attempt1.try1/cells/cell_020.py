
import numpy as np
import datetime

# Load data
sst_base = np.load('sst_base.npy')
base_times_int = np.load('base_times.npy')
base_times = base_times_int.astype('datetime64[D]')

def date_to_doy(dates):
    month_offsets = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335], dtype=np.int64)
    doys = np.zeros(len(dates), dtype=np.int64)
    for i, d in enumerate(dates):
        dt = np.datetime64(d, 'D').astype(datetime.datetime)
        doys[i] = month_offsets[dt.month - 1] + dt.day
    return doys

# Baseline indices in extended array
bl_start_idx = 5  # 1992-01-01
bl_end_idx = 4022  # 2002-12-31
baseline_dates = base_times[bl_start_idx:bl_end_idx+1]
baseline_doy = date_to_doy(baseline_dates)

# Build pool indices for each doy
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

print("Pool indices built. sst_base shape:", sst_base.shape)

# Compute threshold and climatology for each doy (except 60)
# Shape: (366, 60, 60) for both
thresholds = np.full((366, 60, 60), np.nan)
climatologies = np.full((366, 60, 60), np.nan)

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

print("Thresholds shape:", thresholds.shape)
print("Climatologies shape:", climatologies.shape)
print("Sample thresholds (doy 153, first 3 cells):", thresholds[152, 0, :3])
print("Sample climatologies (doy 153, first 3 cells):", climatologies[152, 0, :3])

# Check for NaN in thresholds and climatologies
print("NaN in thresholds:", np.isnan(thresholds).sum())
print("NaN in climatologies:", np.isnan(climatologies).sum())

# Save intermediate results
np.save('thresholds_raw.npy', thresholds)
np.save('climatologies_raw.npy', climatologies)
