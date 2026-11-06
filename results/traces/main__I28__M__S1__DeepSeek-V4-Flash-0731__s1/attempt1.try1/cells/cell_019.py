
import numpy as np
from datetime import date, timedelta
import xarray as xr
import os

def doy_of_date(d):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[d.month-1] + d.day

# Load region coordinates
ds0 = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20130601.nc', engine='h5netcdf')
lat_all = ds0['latitude'].values
lon_all = ds0['longitude'].values
lat_idx = np.where((lat_all >= 57.85) & (lat_all <= 59.05))[0]
lon_idx = np.where((lon_all >= 21.01) & (lon_all <= 22.21))[0]
ds0.close()
nlat, nlon = len(lat_idx), len(lon_idx)

# Load target data to identify sea cells
target_start = date(2013, 6, 1)
target_end = date(2013, 8, 31)
target_sst = []
target_dates = []
d = target_start
while d <= target_end:
    fname = f"/data/icsa2027_data_20261101T090944Z/s1z/sst_{d.strftime('%Y%m%d')}.nc"
    ds = xr.open_dataset(fname, engine='h5netcdf')
    target_sst.append(ds['analysed_sst'].values[0, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1])
    target_dates.append(d)
    ds.close()
    d += timedelta(days=1)
target_sst = np.array(target_sst)
sea_mask = np.all(np.isfinite(target_sst), axis=0)
print("Sea cells:", sea_mask.sum(), "Non-sea:", (~sea_mask).sum())

# Now load a small portion of baseline to check NaN patterns
# Check doy 153 pool for a specific cell
base_start = date(1991, 12, 27)
base_end = date(2003, 1, 5)
all_dates = []
d = base_start
while d <= base_end:
    all_dates.append(d)
    d += timedelta(days=1)
date_to_idx = {d: i for i, d in enumerate(all_dates)}
baseline_1992_2002 = [d for d in all_dates if date(1992,1,1) <= d <= date(2002,12,31)]

# Load baseline for a subset of cells to check NaN patterns
# Let's load baseline data for all cells in the region
baseline_sst = np.zeros((len(all_dates), nlat, nlon), dtype=np.float64)
for i, d in enumerate(all_dates):
    fname = f"/data/icsa2027_data_20261101T090944Z/s1z/sst_{d.strftime('%Y%m%d')}.nc"
    ds = xr.open_dataset(fname, engine='h5netcdf')
    baseline_sst[i] = ds['analysed_sst'].values[0, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1]
    ds.close()

# Check which cells have valid baseline data at doy 153
# Build pool for doy 153
doy = 153
pool = []
for D in baseline_1992_2002:
    if doy_of_date(D) == doy:
        for k in range(-5, 6):
            X = D + timedelta(days=k)
            if X in date_to_idx:
                pool.append(date_to_idx[X])
pool = np.array(pool)
pool_data = baseline_sst[pool]  # (n_pool, nlat, nlon)
valid_count = np.sum(np.isfinite(pool_data), axis=0)
nan_cells = valid_count == 0
print("Cells with no valid data in doy 153 pool:", nan_cells.sum())

# Check if these match non-sea cells
non_sea = ~sea_mask
print("Overlap of NaN cells and non-sea cells:", np.sum(nan_cells & non_sea))
print("NaN cells that are sea:", np.sum(nan_cells & sea_mask))
print("Non-sea cells with valid data:", np.sum(non_sea & ~nan_cells))
