
import numpy as np
from datetime import date, timedelta
import xarray as xr

def doy_of_date(d):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[d.month-1] + d.day

# Load data
ds0 = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20130601.nc', engine='h5netcdf')
lat_all = ds0['latitude'].values
lon_all = ds0['longitude'].values
lat_idx = np.where((lat_all >= 57.85) & (lat_all <= 59.05))[0]
lon_idx = np.where((lon_all >= 21.01) & (lon_all <= 22.21))[0]
ds0.close()

base_start = date(1991, 12, 27)
base_end = date(2003, 1, 5)
all_dates = []
d = base_start
while d <= base_end:
    all_dates.append(d)
    d += timedelta(days=1)
date_to_idx = {d: i for i, d in enumerate(all_dates)}
baseline_1992_2002 = [d for d in all_dates if date(1992,1,1) <= d <= date(2002,12,31)]

# Build pool for doy 153
doy = 153
pool = []
for D in baseline_1992_2002:
    if doy_of_date(D) == doy:
        for k in range(-5, 6):
            X = D + timedelta(days=k)
            if X in date_to_idx:
                pool.append(date_to_idx[X])

# Load cell (0,0) values
cell_values = []
for pi in pool:
    d = all_dates[pi]
    fname = f"/data/icsa2027_data_20261101T090944Z/s1z/sst_{d.strftime('%Y%m%d')}.nc"
    ds = xr.open_dataset(fname, engine='h5netcdf')
    val = float(ds['analysed_sst'].values[0, lat_idx[0], lon_idx[0]])
    cell_values.append(val)
    ds.close()

cell_values = np.array(cell_values)
valid = cell_values[np.isfinite(cell_values)]

# numpy hazen
np_p90 = np.percentile(valid, 90, method='hazen')
print(f"numpy hazen p90: {np_p90}")

# Also try mean
np_mean = np.mean(valid)
print(f"numpy mean: {np_mean}")

# Check what the threshold should be - what did the main script compute?
# Let me load the threshold array
threshold = np.load('/tmp/threshold.npy')
print(f"threshold[152, 0, 0] from saved array: {threshold[152, 0, 0]}")

# Also check what cell (0,0) corresponds to in the region
print(f"Cell (0,0) is at lat={lat_all[lat_idx[0]]}, lon={lon_all[lon_idx[0]]}")
print(f"Is cell (0,0) a sea cell? ")
sea_mask = np.load('/tmp/sea_mask.npy')
print(f"  sea_mask[0,0] = {sea_mask[0,0]}")

# Let me also check: does the saved threshold[152,0,0] differ from what we'd compute?
# Let me check if there might be a subtle difference in how values are stored
# The baseline_sst array in the main script stored the values as float64
# Let me check if float32 -> float64 conversion causes differences

# Actually, let me just check the sorted values at positions k and k+1
sorted_vals = np.sort(valid)
N = len(sorted_vals)
p = 0.9
h = (N - 1) * p
k = int(np.floor(h))
g = h - k
print(f"N={N}, h={h}, k={k}, g={g}")
print(f"sorted_vals[{k}] = {sorted_vals[k]}")
print(f"sorted_vals[{k+1}] = {sorted_vals[k+1]}")
manual = (1-g) * sorted_vals[k] + g * sorted_vals[k+1]
print(f"manual p90 = {manual}")
print(f"np hazen p90 = {np_p90}")
print(f"Match: {abs(manual - np_p90) < 1e-10}")
