
import numpy as np
import pandas as pd
import xarray as xr

# Reload data
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

lat = ds.latitude.values
lon = ds.longitude.values
time = pd.to_datetime(ds.time.values)

lat_idx = np.where((lat >= 56.09) & (lat <= 57.29))[0]
lon_idx = np.where((lon >= 10.55) & (lon <= 11.75))[0]

# Baseline: 1991-12-27 to 2003-01-05
mask = (time >= pd.Timestamp('1991-12-27')) & (time <= pd.Timestamp('2003-01-05'))
idx_base = np.where(mask)[0]

# Target: 2009-06-01 to 2009-08-31
mask_t = (time >= pd.Timestamp('2009-06-01')) & (time <= pd.Timestamp('2009-08-31'))
idx_target = np.where(mask_t)[0]

base_time = time[idx_base]
target_time = time[idx_target]

# Read data as float64
base_sst = ds['analysed_sst'].isel(time=idx_base, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)
target_sst = ds['analysed_sst'].isel(time=idx_target, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)

print("base_sst shape:", base_sst.shape)
print("target_sst shape:", target_sst.shape)

# Step 1: Sea cells - finite SST on every day of target period
n_lat = len(lat_idx)
n_lon = len(lon_idx)
n_target = len(idx_target)

sea_cells = np.zeros((n_lat, n_lon), dtype=bool)
for i in range(n_lat):
    for j in range(n_lon):
        sea_cells[i,j] = np.all(np.isfinite(target_sst[:, i, j]))

print(f"Sea cells: {sea_cells.sum()} out of {n_lat*n_lon}")

# Step 2: Threshold and climatology per sea cell and day of year
def date_to_doy(dt):
    month = dt.month
    day = dt.day
    days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return days_before[month-1] + day

# For each day of year d (1-366), find which baseline dates map to it
# Then for each d != 60, the pool is all SST values whose date is within ±5 calendar days
# of a baseline date whose day of year is d.
# Wait - let me re-read the instructions more carefully.

# "For each day of year d other than 60, the pool is every SST value whose date lies within ±5 calendar days
# of a baseline date (1992-01-01 to 2002-12-31) whose day of year is d."

# So for each d != 60:
# - Find all baseline dates (1992-01-01 to 2002-12-31) whose day of year is d
# - For each such date, include all SST values from dates within ±5 calendar days
# - The ±5 window extends to 1991-12-27 and 2003-01-05

# Actually wait. Let me re-read more carefully:
# "For each day of year d other than 60, the pool is every SST value whose date lies within ±5 calendar days
# of a baseline date (1992-01-01 to 2002-12-31) whose day of year is d."

# So we look at each date in the baseline period [1992-01-01, 2002-12-31],
# compute its day of year d, and if d != 60, then all SST values from
# dates within ±5 days of that baseline date go into pool d.

# "Windows near the ends of the baseline reach up to 5 days beyond it (1991-12-27 to 1991-12-31 and 2003-01-01 to 2003-01-05); include those days."

# So the ±5 day windows can extend to 1991-12-27 and 2003-01-05.

# "29 February values belong to the windows of their calendar neighbours."
# So Feb 29 SST values go into the windows of Feb 28 and Mar 1 (days 59 and 61).

# So effectively: for each day d != 60, we collect all SST values from dates that are
# within ±5 calendar days of some baseline date whose day-of-year is d.
# And also Feb 29 values get included in the pools for days 59 and 61 via their neighbors.

print("\nBuilding pools...")

# First, let me map each date in the full baseline window (1991-12-27 to 2003-01-05)
# to its day of year and also to which "pool" it belongs.

# The baseline dates are those in [1992-01-01, 2002-12-31]
base_start_full = pd.Timestamp('1991-12-27')
base_end_full = pd.Timestamp('2003-01-05')

# For each day d in 1..366 (except 60), the pool consists of all SST values from dates
# that are within ±5 calendar days of a baseline date whose day-of-year is d.

# Let me build this differently. For each date t in the full window [1991-12-27, 2003-01-05],
# check if there exists a baseline date (in [1992-01-01, 2002-12-31]) with day-of-year d
# such that |t - baseline_date| <= 5 days. If so, t contributes to pool d.

# More precisely: for each d != 60, for each baseline date B in [1992-01-01, 2002-12-31] 
# with doy(B) = d, for each date t with |t - B| <= 5 days (calendar days), 
# add SST(t) to pool d.

# The baseline years 1992-2002 include leap years: 1992, 1996, 2000.
# Non-leap years have no day 60.
# In leap years, Feb 29 = day 60, but we don't use day 60 as a pool.
# 29 February values belong to the windows of their calendar neighbours (days 59 and 61).

# Let me implement this by:
# 1. Computing doy for every baseline date
# 2. For each baseline date with doy != 60, collecting all dates within ±5 days
# 3. Grouping by doy

# Actually, I think the cleanest interpretation is:
# For each d (1-366, d != 60):
#   - Find all baseline dates B (1992-01-01 to 2002-12-31) with doy(B) = d
#   - For each such B, include all dates t with |t - B| <= 5 days
#   - All SST values at these dates go into pool d

# And "29 February values belong to the windows of their calendar neighbours" means
# that if Feb 29 is within ±5 days of a baseline date with doy 59 or 61,
# then the Feb 29 values are included in those pools. This would happen naturally
# because Feb 29 is Feb 28 + 1 day and Mar 1 - 1 day.

# Let me think about this more carefully with specific dates:
# Baseline date Feb 28, 2000 (doy 59). Its ±5 window includes Feb 23 to Mar 4.
# That includes Feb 29, 2000. So Feb 29, 2000 values are in pool 59. ✓
# Baseline date Mar 1, 2000 (doy 61). Its ±5 window includes Feb 24 to Mar 6.
# That includes Feb 29, 2000. So Feb 29, 2000 values are in pool 61. ✓

# For non-leap years, there's no Feb 29 anyway.

# But wait - in non-leap years, what about the days around Feb 28/Mar 1?
# Feb 28 = doy 59, Mar 1 = doy 61. Non-leap year Feb has only 28 days.
# In non-leap years, Mar 1 = day 60 in real calendar but doy 61 in our mapping.
# Hmm, let me re-read the mapping again.
# "1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61"
# So this is a fixed calendar where Feb always has 28 days + one extra on leap years.

# OK so in non-leap years, Mar 1 is doy 61. In leap years, Feb 29 is doy 60 and Mar 1 is doy 61.

# So for the pool construction, baseline dates in [1992-01-01, 2002-12-31] with doy != 60:
# Each such baseline date has a ±5 day window. All SST values in those windows go into the pool for that doy.

# Let me now implement this properly.

print("Mapping baseline dates to day-of-year...")

# Get all dates in the full baseline window
full_base_idx = np.where((time >= pd.Timestamp('1991-12-27')) & (time <= pd.Timestamp('2003-01-05')))[0]
full_base_time = time[full_base_idx]
full_base_sst = base_sst  # This already covers the full window

# Actually, base_sst was already sliced with idx_base which covers [1991-12-27, 2003-01-05]
print("Full baseline time range:", full_base_time[0], "to", full_base_time[-1])
print("Full baseline count:", len(full_base_time))

# Check: baseline dates that count as "baseline" are in [1992-01-01, 2002-12-31]
base_dates_mask = (full_base_time >= pd.Timestamp('1992-01-01')) & (full_base_time <= pd.Timestamp('2002-12-31'))
base_dates = full_base_time[base_dates_mask]
print("Official baseline dates:", base_dates[0], "to", base_dates[-1], "count:", len(base_dates))

# For each official baseline date, compute doy
base_doys = np.array([date_to_doy(d) for d in base_dates])
print("Baseline doy range:", base_doys.min(), base_doys.max())

# Now for each day d (1-366, d != 60), collect all SST values from dates
# within ±5 calendar days of baseline dates with doy == d.

# Strategy: for each doy d, find all baseline dates B with doy(B)=d.
# Then for each such B, the pool includes all dates t where |t-B| <= 5 days.
# Since we have the full data for [1991-12-27, 2003-01-05], we can just check
# each date in the full window.

print("\nBuilding pools for each day of year...")

n_doy = 366
pools = {}  # doy -> list of SST values (flattened)

# For each doy d != 60
for d in range(1, n_doy+1):
    if d == 60:
        continue
    # Find baseline dates with doy == d
    bd_mask = (base_doys == d)
    bd_indices = np.where(bd_mask)[0]
    if len(bd_indices) == 0:
        pools[d] = []
        continue
    
    # Find all dates in full window that are within ±5 days of any baseline date with doy==d
    # For each baseline date B, dates t with |t-B| <= 5 days
    pool_dates = set()
    for bi in bd_indices:
        B = base_dates[bi]
        for dt in range(-5, 6):
            candidate = B + pd.Timedelta(days=dt)
            pool_dates.add(candidate)
    
    # Convert to indices in full_base_time
    pool_mask = np.array([t in pool_dates for t in full_base_time])
    pool_sst = full_base_sst[pool_mask]  # (n_dates, n_lat, n_lon)
    pools[d] = pool_sst

print("Done building pools.")
# Check pool sizes for a few doys
for d in [1, 59, 61, 182, 366]:
    if d in pools:
        print(f"doy {d}: pool has {pools[d].shape} values per cell" if len(pools[d]) > 0 else f"doy {d}: empty")
