
import numpy as np
import pandas as pd
import xarray as xr

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat = ds.latitude.values
lon = ds.longitude.values
time = pd.to_datetime(ds.time.values)

lat_idx = np.where((lat >= 56.09) & (lat <= 57.29))[0]
lon_idx = np.where((lon >= 10.55) & (lon <= 11.75))[0]

# Pick a specific sea cell to verify
# Let me find a sea cell index
mask = (time >= pd.Timestamp('1991-12-27')) & (time <= pd.Timestamp('2003-01-05'))
idx_base = np.where(mask)[0]
mask_t = (time >= pd.Timestamp('2009-06-01')) & (time <= pd.Timestamp('2009-08-31'))
idx_target = np.where(mask_t)[0]

base_time = time[idx_base]
target_time = time[idx_target]

base_sst = ds['analysed_sst'].isel(time=idx_base, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)
target_sst = ds['analysed_sst'].isel(time=idx_target, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)

# Sea cells
n_lat, n_lon = 60, 60
sea_cells = np.zeros((n_lat, n_lon), dtype=bool)
for i in range(n_lat):
    for j in range(n_lon):
        sea_cells[i,j] = np.all(np.isfinite(target_sst[:, i, j]))

# Find first sea cell
sea_indices = np.where(sea_cells)
print("First sea cell:", sea_indices[0][0], sea_indices[1][0])

def date_to_doy(dt):
    month = dt.month
    day = dt.day
    days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return days_before[month-1] + day

# Let me verify the threshold for a specific cell and doy
i, j = sea_indices[0][0], sea_indices[1][0]
print(f"\nCell ({i}, {j}), lat={lat[lat_idx[i]]}, lon={lon[lon_idx[j]]}")

# Target doys
target_doys = np.array([date_to_doy(t) for t in target_time])
print("Target doys:", target_doys)

# Build pools for this cell
full_base_time = base_time
base_dates_mask = (full_base_time >= pd.Timestamp('1992-01-01')) & (full_base_time <= pd.Timestamp('2002-12-31'))
base_dates = full_base_time[base_dates_mask]
base_doys = np.array([date_to_doy(d) for d in base_dates])

# For a target doy, say doy 200 (July 19)
d_test = 200
bd_mask = (base_doys == d_test)
bd_dates = base_dates[bd_mask]
print(f"\nDoy {d_test}: {len(bd_dates)} baseline dates")
for B in bd_dates:
    print(f"  {B.strftime('%Y-%m-%d')}")

# Collect pool dates
pool_date_set = set()
for B in bd_dates:
    for delta in range(-5, 6):
        pool_date_set.add(B + pd.Timedelta(days=delta))

pool_dates_list = sorted(pool_date_set)
print(f"Pool has {len(pool_dates_list)} dates")

# Get pool values for this cell
pool_mask = np.array([t in pool_date_set for t in full_base_time])
pool_vals = base_sst[pool_mask, i, j]
valid = pool_vals[np.isfinite(pool_vals)]
print(f"Valid values in pool: {len(valid)}")

# Compute threshold
thr = np.quantile(valid, 0.9, method='hazen')
clim = np.mean(valid)
print(f"Raw threshold: {thr}")
print(f"Raw climatology: {clim}")
print(f"SST range in pool: {valid.min():.2f} to {valid.max():.2f}")
