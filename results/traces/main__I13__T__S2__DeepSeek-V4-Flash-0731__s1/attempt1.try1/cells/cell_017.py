
import numpy as np
import datetime

# Load saved data
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
# pool_indices[d] = sorted list of indices into extended baseline array
pool_indices = {}

for d in range(1, 367):
    if d == 60:
        continue
    # Find baseline indices with this doy
    bl_where = np.where(baseline_doy == d)[0]
    bl_abs_idx = bl_where + bl_start_idx  # indices into extended array
    
    # Collect all dates within ±5 days of each baseline date
    all_indices = set()
    for bi in bl_abs_idx:
        B = base_times[bi]
        lo = B - np.timedelta64(5, 'D')
        hi = B + np.timedelta64(5, 'D')
        t_lo = np.searchsorted(base_times, lo)
        t_hi = np.searchsorted(base_times, hi, side='right')
        all_indices.update(range(t_lo, t_hi))
    
    pool_indices[d] = sorted(all_indices)

# Check some pool sizes
for d in [1, 2, 59, 61, 100, 153, 244, 366]:
    print(f"doy {d}: pool size = {len(pool_indices[d])}")
    if len(pool_indices[d]) > 0:
        idx = pool_indices[d]
        print(f"  Dates: {base_times[idx[0]]} to {base_times[idx[-1]]}")

# Verify doy 60 has no pool
print(f"doy 60: no pool (as expected)")

# Save pool_indices
np.save('pool_indices.npy', np.array([np.array(pool_indices[d], dtype=np.int64) for d in range(1, 367) if d != 60], dtype=object), allow_pickle=True)
