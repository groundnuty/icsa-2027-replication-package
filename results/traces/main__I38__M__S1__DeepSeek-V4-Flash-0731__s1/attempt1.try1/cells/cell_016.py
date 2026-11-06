
import xarray as xr
import numpy as np
from datetime import date, timedelta
import os, time, json

data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'
intermediate_dir = 'intermediate'
os.makedirs(intermediate_dir, exist_ok=True)
os.makedirs('output', exist_ok=True)

# Day of year mapping
def day_of_year(d):
    month_days = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:d.month]) + d.day

# ===== Setup =====
# Build pool dates for each doy
baseline_start = date(1992, 1, 1)
baseline_end = date(2002, 12, 31)

doy_to_baseline_dates = {}
d = baseline_start
while d <= baseline_end:
    doy = day_of_year(d)
    if doy not in doy_to_baseline_dates:
        doy_to_baseline_dates[doy] = []
    doy_to_baseline_dates[doy].append(d)
    d += timedelta(days=1)

doy_to_pool_dates = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    pool_dates = set()
    for b in doy_to_baseline_dates.get(doy, []):
        for i in range(-5, 6):
            pool_dates.add(b + timedelta(days=i))
    doy_to_pool_dates[doy] = sorted(pool_dates)

all_baseline_dates = sorted(set().union(*doy_to_pool_dates.values()))

# Target dates
target_start = date(2003, 6, 1)
target_end = date(2003, 8, 31)
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += timedelta(days=1)

# Region indices
ds = xr.open_dataset(f'{data_dir}/sst_19920101.nc', engine='h5netcdf')
lats = ds.latitude.values
lons = ds.longitude.values
lat_idx = np.where((lats >= 60.49) & (lats <= 61.69))[0]
lon_idx = np.where((lons >= 17.25) & (lons <= 18.45))[0]
region_lats = lats[lat_idx]
region_lons = lons[lon_idx]
ds.close()

# Save metadata
np.save(f'{intermediate_dir}/lat_idx.npy', lat_idx)
np.save(f'{intermediate_dir}/lon_idx.npy', lon_idx)
np.save(f'{intermediate_dir}/region_lats.npy', region_lats)
np.save(f'{intermediate_dir}/region_lons.npy', region_lons)

# Save dates as strings
with open(f'{intermediate_dir}/metadata.json', 'w') as f:
    json.dump({
        'baseline_dates': [d.isoformat() for d in all_baseline_dates],
        'target_dates': [d.isoformat() for d in target_dates],
        'lat_idx_start': int(lat_idx[0]),
        'lat_idx_end': int(lat_idx[-1]),
        'lon_idx_start': int(lon_idx[0]),
        'lon_idx_end': int(lon_idx[-1]),
    }, f)

print(f"Baseline dates: {len(all_baseline_dates)}")
print(f"Target dates: {len(target_dates)}")
print(f"Region: {len(lat_idx)} lat x {len(lon_idx)} lon")

# Save doy_to_pool_dates
doy_pool_dates_json = {}
for doy, dates in doy_to_pool_dates.items():
    doy_pool_dates_json[str(doy)] = [d.isoformat() for d in dates]
with open(f'{intermediate_dir}/doy_pool_dates.json', 'w') as f:
    json.dump(doy_pool_dates_json, f)

# ===== Load baseline data =====
baseline_date_to_idx = {d: i for i, d in enumerate(all_baseline_dates)}
baseline_sst = np.full((len(all_baseline_dates), len(lat_idx), len(lon_idx)), np.nan, dtype=np.float32)

print("Loading baseline data...")
t0 = time.time()
for i, dt in enumerate(all_baseline_dates):
    fname = f'{data_dir}/sst_{dt.strftime("%Y%m%d")}.nc'
    ds = xr.open_dataset(fname, engine='h5netcdf')
    baseline_sst[i] = ds.analysed_sst.values[0, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1]
    ds.close()
    if (i+1) % 500 == 0:
        print(f"  Loaded {i+1}/{len(all_baseline_dates)}, elapsed: {time.time()-t0:.1f}s")

print(f"Baseline loaded in {time.time()-t0:.1f}s")
np.save(f'{intermediate_dir}/baseline_sst.npy', baseline_sst)
print(f"Baseline saved, size: {baseline_sst.nbytes/1e6:.1f} MB")
