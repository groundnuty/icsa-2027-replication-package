
import numpy as np
import xarray as xr
from datetime import date, timedelta

def doy_of_date(d):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[d.month-1] + d.day

# Load intermediate data
threshold = np.load('/tmp/threshold.npy')
target_sst = np.load('/tmp/target_sst.npy')
sea_mask = np.load('/tmp/sea_mask.npy')
target_dates_str = np.load('/tmp/target_dates_str.npy', allow_pickle=True)

# Verify threshold computation for a specific cell and doy
# Let's pick doy 153 (Jun 1) and cell (0, 0)
# Recompute the pool and verify the Hazen percentile manually

base_start = date(1991, 12, 27)
base_end = date(2003, 1, 5)
all_dates = []
d = base_start
while d <= base_end:
    all_dates.append(d)
    d += timedelta(days=1)
date_to_idx = {d: i for i, d in enumerate(all_dates)}
baseline_1992_2002 = [d for d in all_dates if date(1992,1,1) <= d <= date(2002,12,31)]

# Load baseline data for one cell to verify
ds0 = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20130601.nc', engine='h5netcdf')
lat_all = ds0['latitude'].values
lon_all = ds0['longitude'].values
lat_idx = np.where((lat_all >= 57.85) & (lat_all <= 59.05))[0]
lon_idx = np.where((lon_all >= 21.01) & (lon_all <= 22.21))[0]
ds0.close()

# Build pool for doy 153 and get values for cell (0,0)
doy = 153
pool = []
for D in baseline_1992_2002:
    if doy_of_date(D) == doy:
        for k in range(-5, 6):
            X = D + timedelta(days=k)
            if X in date_to_idx:
                pool.append(date_to_idx[X])

# Load baseline values for cell (0,0)
cell_values = []
for pi in pool:
    d = all_dates[pi]
    fname = f"/data/icsa2027_data_20261101T090944Z/s1z/sst_{d.strftime('%Y%m%d')}.nc"
    ds = xr.open_dataset(fname, engine='h5netcdf')
    val = ds['analysed_sst'].values[0, lat_idx[0], lon_idx[0]]
    cell_values.append(val)
    ds.close()

cell_values = np.array(cell_values, dtype=np.float64)
valid = cell_values[np.isfinite(cell_values)]
print(f"Cell (0,0) doy 153 pool: {len(valid)} valid values out of {len(cell_values)}")
print(f"First 10 values: {valid[:10]}")

# Compute Hazen percentile manually
sorted_vals = np.sort(valid)
N = len(sorted_vals)
p = 0.9
h = (N - 1) * p
k = int(np.floor(h))
g = h - k
if k >= N - 1:
    manual_p90 = sorted_vals[-1]
else:
    manual_p90 = (1 - g) * sorted_vals[k] + g * sorted_vals[k + 1]

print(f"Manual Hazen p90: {manual_p90}")
print(f"numpy p90: {threshold[152, 0, 0]}")
print(f"Match: {abs(manual_p90 - threshold[152, 0, 0]) < 1e-10}")

# Verify mean
print(f"Manual mean: {np.mean(valid)}")
print(f"numpy mean: {np.mean(valid)}")
print(f"Match: {abs(np.mean(valid) - threshold[152, 0, 0]) < 1e-10}")  # This checks against threshold, not climatology
