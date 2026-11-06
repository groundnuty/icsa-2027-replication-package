
import numpy as np
import datetime as dt

def day_of_year(ts):
    d = dt.datetime.fromtimestamp(ts.astype('datetime64[ns]').astype(np.int64) / 1e9, tz=dt.timezone.utc)
    year = d.year
    month = d.month
    day = d.day
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
    if is_leap:
        days_in_month[1] = 29
    std_doy = sum(days_in_month[:month-1]) + day
    if not is_leap and month > 2:
        std_doy += 1
    return std_doy

# Reload necessary data
base_data = np.load('/tmp/base_data.npy')
base_times = np.load('/tmp/base_times.npy')
base_doy = np.load('/tmp/base_doy.npy')
threshold_raw = np.load('/tmp/threshold_raw.npy')

# Rebuild pools for day 153
base_start = np.datetime64('1992-01-01')
base_end = np.datetime64('2002-12-31')
is_baseline = (base_times >= base_start) & (base_times <= base_end)
baseline_idx = np.where(is_baseline)[0]

epoch = np.datetime64('1970-01-01')
base_days = (base_times - epoch).astype(np.int64) // (24*3600*10**9)

# Pool for day 153
d = 153
d_indices = baseline_idx[base_doy[baseline_idx] == d]
pool_set = set()
for i in d_indices:
    t_i = base_days[i]
    mask = np.abs(base_days - t_i) <= 5
    pool_set.update(np.where(mask)[0].tolist())
pool = sorted(pool_set)
print(f"Day {d} pool size: {len(pool)}")

# For cell (0,0), compute the 90th percentile manually
i, j = 0, 0
pool_data = base_data[pool, i, j].astype(np.float64)
valid = pool_data[~np.isnan(pool_data)]
print(f"Valid values in pool: {len(valid)}")

# Manual hazen quantile
p = 0.9
n = len(valid)
sorted_vals = np.sort(valid)
h = n * p + 0.5
h_floor = int(np.floor(h))
h_ceil = int(np.ceil(h))
print(f"n={n}, h={h}, h_floor={h_floor}, h_ceil={h_ceil}")
print(f"Values at h_floor-1: {sorted_vals[max(0,h_floor-1)]} (index {h_floor-1})")
print(f"Values at h_ceil-1: {sorted_vals[min(n-1,h_ceil-1)]} (index {h_ceil-1})")

# Hazen interpolation
if h_floor == h_ceil:
    manual_q = sorted_vals[h_floor-1]
else:
    manual_q = sorted_vals[h_floor-1] + (h - h_floor) * (sorted_vals[h_ceil-1] - sorted_vals[h_floor-1])

print(f"Manual hazen 90th percentile: {manual_q:.6f}")
print(f"numpy quantile (hazen): {np.quantile(valid, 0.9, method='hazen'):.6f}")
print(f"My computed threshold: {threshold_raw[d, i, j]:.6f}")
print(f"Match numpy: {abs(manual_q - np.quantile(valid, 0.9, method='hazen')) < 1e-10}")
print(f"Match computed: {abs(manual_q - threshold_raw[d, i, j]) < 1e-6}")

# Also verify mean
manual_mean = np.mean(valid)
print(f"\nManual mean: {manual_mean:.6f}")
print(f"numpy mean: {np.mean(valid):.6f}")
