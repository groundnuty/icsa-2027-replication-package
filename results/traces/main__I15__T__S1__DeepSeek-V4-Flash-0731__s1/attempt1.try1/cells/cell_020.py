import numpy as np
import xarray as xr
import fsspec
from datetime import datetime, timedelta

# Define doy mapping
def date_to_doy(year, month, day):
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month-1] + day

# Reload data
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

t_vals = ds.time.values
base_start = np.datetime64('1991-12-27')
base_end = np.datetime64('2003-01-05')
b_idx = np.where((t_vals >= base_start) & (t_vals <= base_end))[0]

t_start = np.datetime64('2019-06-01')
t_end = np.datetime64('2019-08-31')
t_idx = np.where((t_vals >= t_start) & (t_vals <= t_end))[0]

lat_vals = ds.latitude.values
lon_vals = ds.longitude.values
lat_mask = (lat_vals >= 56.13) & (lat_vals <= 57.33)
lon_mask = (lon_vals >= 17.71) & (lon_vals <= 18.91)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]

baseline_sst = ds['analysed_sst'].isel(time=b_idx, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)

# Build date objects
b_dates = []
for i in range(len(b_idx)):
    ts = t_vals[b_idx[i]]
    dt = datetime.utcfromtimestamp(ts.astype('datetime64[us]').astype(np.int64) / 1e6)
    b_dates.append(dt)

date_to_idx = {dt: i for i, dt in enumerate(b_dates)}

# Build core baseline dates
base_core_start = datetime(1992, 1, 1)
base_core_end = datetime(2002, 12, 31)
core_dates = []
for dt in b_dates:
    if base_core_start <= dt <= base_core_end:
        core_dates.append((dt, date_to_doy(dt.year, dt.month, dt.day)))

# Build pools
pools = {d: set() for d in range(1, 367) if d != 60}
for b_dt, b_doy in core_dates:
    if b_doy == 60:
        continue
    for delta in range(-5, 6):
        t = b_dt + timedelta(days=delta)
        if t in date_to_idx:
            pools[b_doy].add(date_to_idx[t])

for d in pools:
    pools[d] = sorted(pools[d])

# Manual check for one cell and one doy
# Cell (0, 0) and doy 153 (June 2)
cell_i, cell_j = 0, 0
doy_test = 153  # June 2

# Get pool indices for doy 153
pool_idxs = pools[doy_test]
pool_values = baseline_sst[pool_idxs, cell_i, cell_j]
print(f"Pool for doy {doy_test}, cell ({cell_i},{cell_j}):")
print(f"  Number of dates: {len(pool_idxs)}")
print(f"  Values: {pool_values}")
print(f"  NaN values: {np.isnan(pool_values).sum()}")
print(f"  Mean: {np.nanmean(pool_values):.6f}")
print(f"  90th percentile (Hazen): {np.nanpercentile(pool_values, 90, method='hazen'):.6f}")

# Verify with manual Hazen calculation
# Hyndman-Fan type 5 (Hazen): 
# h = (N+1) * p (or (N-1)*p+1, let me check)
# Actually, for type 5: h = (N + 1) * p, and value = x_floor(h) + (h - floor(h)) * (x_ceil(h) - x_floor(h))
# where p = percentile/100

p = 0.9
valid = pool_values[~np.isnan(pool_values)]
sorted_vals = np.sort(valid)
n = len(sorted_vals)
print(f"\n  Manual check - sorted values ({n} values):")
print(f"  First few: {sorted_vals[:5]}")
print(f"  Last few: {sorted_vals[-5:]}")

# Hazen (type 5): h = (N+1)*p
h = (n + 1) * p
print(f"  h = ({n}+1)*{p} = {h}")
lo = int(np.floor(h)) - 1  # 0-indexed
hi = int(np.ceil(h)) - 1
if lo == hi:
    result = sorted_vals[lo]
else:
    frac = h - np.floor(h)
    result = sorted_vals[lo] + frac * (sorted_vals[hi] - sorted_vals[lo])
print(f"  Manual Hazen percentile: {result:.6f}")
print(f"  numpy method='hazen': {np.nanpercentile(pool_values, 90, method='hazen'):.6f}")
print(f"  Match: {abs(result - np.nanpercentile(pool_values, 90, method='hazen')) < 1e-10}")
