
import numpy as np
import datetime as dt
import pickle

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

base_data = np.load('/tmp/base_data.npy')
target_data = np.load('/tmp/target_data.npy')
base_times = np.load('/tmp/base_times.npy')
tgt_times = np.load('/tmp/tgt_times.npy')
base_doy = np.load('/tmp/base_doy.npy')
tgt_doy = np.load('/tmp/tgt_doy.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

# Build pools
base_start = np.datetime64('1992-01-01')
base_end = np.datetime64('2002-12-31')
is_baseline = (base_times >= base_start) & (base_times <= base_end)
baseline_idx = np.where(is_baseline)[0]

epoch = np.datetime64('1970-01-01')
base_days = (base_times - epoch).astype(np.int64) // (24*3600*10**9)

pools = {}
for d in range(1, 367):
    if d == 60:
        continue
    d_indices = baseline_idx[base_doy[baseline_idx] == d]
    if len(d_indices) == 0:
        pools[d] = []
        continue
    pool_set = set()
    for i in d_indices:
        t_i = base_days[i]
        mask = np.abs(base_days - t_i) <= 5
        pool_set.update(np.where(mask)[0].tolist())
    pools[d] = sorted(pool_set)

print("Pools built. Day 1 size:", len(pools[1]), "Day 59 size:", len(pools[59]), "Day 366 size:", len(pools[366]))

# Compute threshold and climatology for each day-of-year and each sea cell
# Convert base_data to float64
base_data_f64 = base_data.astype(np.float64)

# Compute threshold (90th percentile, hazen) and climatology (mean) per day-of-year per cell
n_lat, n_lon = 60, 60
threshold_raw = np.full((367, n_lat, n_lon), np.nan, dtype=np.float64)
climatology_raw = np.full((367, n_lat, n_lon), np.nan, dtype=np.float64)

for d in range(1, 367):
    if d == 60:
        continue
    idx = pools[d]
    if len(idx) == 0:
        continue
    # Extract data for this pool: (pool_size, n_lat, n_lon)
    pool_data = base_data_f64[idx, :, :]
    
    # Compute threshold (90th percentile with hazen method, ignoring NaN)
    # numpy.quantile with method='hazen' per cell
    for i in range(n_lat):
        for j in range(n_lon):
            vals = pool_data[:, i, j]
            valid = vals[~np.isnan(vals)]
            if len(valid) > 0:
                threshold_raw[d, i, j] = np.quantile(valid, 0.9, method='hazen')
                climatology_raw[d, i, j] = np.mean(valid)
    
    if d % 50 == 0:
        print(f"Processed day {d}")

print("Threshold and climatology computed.")

# Set day 60 to mean of days 59 and 61
threshold_raw[60, :, :] = (threshold_raw[59, :, :] + threshold_raw[61, :, :]) / 2
climatology_raw[60, :, :] = (climatology_raw[59, :, :] + climatology_raw[61, :, :]) / 2

# Save intermediate results
np.save('/tmp/threshold_raw.npy', threshold_raw)
np.save('/tmp/climatology_raw.npy', climatology_raw)
print("Saved raw threshold and climatology.")
print("Threshold day 59 sample:", threshold_raw[59, 0, 0] if np.isfinite(threshold_raw[59, 0, 0]) else "NaN")
