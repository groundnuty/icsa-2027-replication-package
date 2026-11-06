
import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import json

# ========== Load data ==========
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

lat_sel = ds.latitude.values
lon_sel = ds.longitude.values
lat_idx = np.where((lat_sel >= 54.13) & (lat_sel <= 55.33))[0]
lon_idx = np.where((lon_sel >= 14.67) & (lon_sel <= 15.87))[0]

# Baseline time: 1991-12-27 to 2003-01-05 (extended)
base_start = np.datetime64('1991-12-27')
base_end = np.datetime64('2003-01-05')
t_idx_base = np.where((ds.time.values >= base_start) & (ds.time.values <= base_end))[0]
base_dates = ds.time.values[t_idx_base]
base_sst = ds.analysed_sst.isel(time=t_idx_base, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)

# Target time: 2008-06-01 to 2008-08-31
tgt_start = np.datetime64('2008-06-01')
tgt_end = np.datetime64('2008-08-31')
t_idx_tgt = np.where((ds.time.values >= tgt_start) & (ds.time.values <= tgt_end))[0]
tgt_dates = ds.time.values[t_idx_tgt]
tgt_sst = ds.analysed_sst.isel(time=t_idx_tgt, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)

# Convert to Python datetime for easier handling
base_dates_py = [datetime.utcfromtimestamp(int(d.astype('datetime64[ns]').astype(np.int64)) / 1e9) for d in base_dates]
tgt_dates_py = [datetime.utcfromtimestamp(int(d.astype('datetime64[ns]').astype(np.int64)) / 1e9) for d in tgt_dates]

print("Base dates:", base_dates_py[0], base_dates_py[-1], "count:", len(base_dates_py))
print("Target dates:", tgt_dates_py[0], tgt_dates_py[-1], "count:", len(tgt_dates_py))

# ========== Determine sea cells ==========
# Cells where SST is finite on every day of the target period
n_tgt = len(tgt_dates_py)
sea_cells = np.all(~np.isnan(tgt_sst), axis=0)  # shape (60, 60)
print("Sea cells:", sea_cells.sum(), "out of", 60*60)

# ========== Build day-of-year pools ==========
days_before_month = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def doy_from_date(dt):
    return days_before_month[dt.month - 1] + dt.day

# Identify baseline dates (1992-01-01 to 2002-12-31)
# These are the dates we use to define pools
# Extended dates are 1991-12-27 to 2003-01-05, we use all of them for pool values

# For each date in the extended baseline, determine which doy pools it contributes to
# A date t contributes to pool d if there's a baseline date B (1992-2002) 
# with doy(B)=d and |t-B| <= 5 days

# Build a mapping from extended date index -> list of doy pools it belongs to
ext_dates = base_dates_py
n_ext = len(ext_dates)

# Baseline dates: those in 1992-2002
baseline_date_indices = [i for i, d in enumerate(ext_dates) 
                         if datetime(1992,1,1) <= d <= datetime(2002,12,31)]
print("Baseline date indices:", len(baseline_date_indices))

# For each baseline date B, its doy
baseline_doy = {i: doy_from_date(ext_dates[i]) for i in baseline_date_indices}

# For each extended date t, find which baseline dates B are within ±5 days
# Then t contributes to pool doy(B) for each such B
from collections import defaultdict
date_to_pools = defaultdict(list)
for i in range(n_ext):
    t = ext_dates[i]
    for j in baseline_date_indices:
        b = ext_dates[j]
        if abs((t - b).days) <= 5:
            d = baseline_doy[j]
            if d != 60:  # day 60 gets no pool of its own
                date_to_pools[i].append(d)

# Verify: for each date, how many pools does it belong to?
pool_counts = [len(date_to_pools[i]) for i in range(n_ext)]
print("Min pools per date:", min(pool_counts), "Max:", max(pool_counts))

# Check: does each doy (except 60) have at least some dates?
all_doys = set()
for i in range(n_ext):
    all_doys.update(date_to_pools[i])
print("Doy values covered:", len(all_doys))
print("Missing doys:", sorted(set(range(1,367)) - all_doys - {60}))
