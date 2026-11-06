
import numpy as np
import pandas as pd
import xarray as xr

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

lat = ds.latitude.values
lon = ds.longitude.values
time = pd.to_datetime(ds.time.values)

lat_idx = np.where((lat >= 56.09) & (lat <= 57.29))[0]
lon_idx = np.where((lon >= 10.55) & (lon <= 11.75))[0]

# Baseline
mask = (time >= pd.Timestamp('1991-12-27')) & (time <= pd.Timestamp('2003-01-05'))
idx_base = np.where(mask)[0]

# Target
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

def date_to_doy(dt):
    month = dt.month
    day = dt.day
    days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return days_before[month-1] + day

# Build pools
full_base_idx = idx_base
full_base_time = base_time

base_dates_mask = (full_base_time >= pd.Timestamp('1992-01-01')) & (full_base_time <= pd.Timestamp('2002-12-31'))
base_dates = full_base_time[base_dates_mask]
base_doys = np.array([date_to_doy(d) for d in base_dates])

# Check pool for doys 59 and 61 - how many distinct dates are in each?
# For doy 59: baseline dates with doy 59 are Feb 28 of each year 1992-2002 (11 years)
# For doy 61: baseline dates with doy 61 are Mar 1 of each year 1992-2002 (11 years)

# Feb 28 of 1992-2002, ±5 days
# Mar 1 of 1992-2002, ±5 days

# For leap years (1992, 1996, 2000), the ±5 window of Feb 28 includes Feb 29,
# and the ±5 window of Mar 1 also includes Feb 29.
# So Feb 29 values appear in both pool 59 and pool 61.

# Let me count dates in pool 59 vs pool 61 for leap vs non-leap years

# Pool 59: union of [Feb 23 to Mar 4] for each year 1992-2002 (doy 59 = Feb 28)
# In leap years: Feb 23-Mar 4 = 11 days (includes Feb 29)
# In non-leap years: Feb 23-Mar 4 = 10 days (no Feb 29, so Feb 23,24,25,26,27,28,Mar 1,2,3,4 = 10 days)

# Wait, Feb 23 to Mar 4 in a non-leap year: Feb has 28 days.
# Feb 23, 24, 25, 26, 27, 28 = 6 days in Feb
# Mar 1, 2, 3, 4 = 4 days in Mar
# Total = 10 days
# In leap year: Feb 23, 24, 25, 26, 27, 28, 29 = 7 days in Feb + 4 days in Mar = 11 days

# 1992-2002 has 3 leap years (1992, 1996, 2000) and 8 non-leap years
# Pool 59 size = 3*11 + 8*10 = 33 + 80 = 113 days

# Pool 61: union of [Feb 24 to Mar 6] for each year 1992-2002 (doy 61 = Mar 1)
# In leap years: Feb 24,25,26,27,28,29 + Mar 1,2,3,4,5,6 = 6+6 = 12 days
# In non-leap years: Feb 24,25,26,27,28 + Mar 1,2,3,4,5,6 = 5+6 = 11 days
# Wait, in non-leap year, Feb 24-28 = 5 days and Mar 1-6 = 6 days, total = 11.
# In leap year, Feb 24-29 = 6 days and Mar 1-6 = 6 days, total = 12.
# Pool 61 size = 3*12 + 8*11 = 36 + 88 = 124 days

# But wait, the pool for doy 59 also includes dates before 1992-01-01 and after 2002-12-31.
# For example, the baseline date Feb 28, 1992, its ±5 window extends to Feb 23, 1992 which is fine.
# And baseline date Feb 28, 2002, its ±5 window extends to Mar 4, 2002 which is fine.
# What about baseline dates at the edges? Dec 31, 2002 has ±5 window extending to Jan 5, 2003.
# And Jan 1, 1992 has ±5 window extending to Dec 27, 1991.

# So the pool for doy 366 (Dec 31) includes dates from Dec 26 to Jan 5.
# For the 11 baseline years (1992-2002), this gives:
#   - Dec 26-31 of each year (6 days × 11 years)
#   - Jan 1-5 of each year (5 days × 11 years)
#   - But Dec 26 of year 1991 is also included (5 days before Jan 1, 1992)
#   - And Jan 5 of 2003 is also included (5 days after Dec 31, 2002)

# So the pool for doy 366 has: Dec 26-31 (6 days) for years 1991-2002 (12 years) + Jan 1-5 (5 days) for years 1992-2003 (12 years)
# = 6*12 + 5*12 = 72 + 60 = 132? That doesn't match the 121 I got.

# Wait, let me reconsider. The baseline dates are only 1992-01-01 to 2002-12-31.
# For doy 366 (Dec 31), the baseline dates with doy=366 are Dec 31 of years 1992-2002.
# That's 11 dates. Each has a ±5 window.
# Dec 31, 1992: Dec 26-31, 1992 + Jan 1-5, 1993
# Dec 31, 2002: Dec 26-31, 2002 + Jan 1-5, 2003
# For each of the 11 years: the window is Dec 26-31 of that year + Jan 1-5 of next year.
# But some windows may overlap between consecutive years.

# Wait, the pool is the union of all dates that fall within ±5 days of ANY baseline date with doy=366.
# So dates from Dec 26, 1991 to Jan 5, 1993 (from Dec 31, 1992's window going back 5 days)
# ... no wait, Dec 31, 1992's window goes from Dec 26, 1992 to Jan 5, 1993.
# Dec 31, 1993's window goes from Dec 26, 1993 to Jan 5, 1994.
# Etc.

# So the union is: Dec 26, 1992 - Jan 5, 1993 (from 1992's window)
#             Dec 26, 1993 - Jan 5, 1994 (from 1993's window)
#             ...
#             Dec 26, 2002 - Jan 5, 2003 (from 2002's window)
# That's 11 windows of 11 days each, non-overlapping. Total 121 days.

# But wait, what about Dec 26, 1991 - Dec 31, 1991? That would be in the window of Dec 31, 1992 going back 5 days... 
# No, Dec 31, 1992 - 5 days = Dec 26, 1992. Not Dec 1991.

# Hmm, but the instructions say "Windows near the ends of the baseline reach up to 5 days beyond it (1991-12-27 to 1991-12-31 and 2003-01-01 to 2003-01-05); include those days."

# This means for Jan 1, 1992 (doy 1), the ±5 window goes back to Dec 27, 1991.
# And for Dec 31, 2002 (doy 366), the ±5 window goes forward to Jan 5, 2003.

# So for doy 1 (Jan 1), the window of Jan 1, 1992 includes Dec 27-31, 1991.
# For doy 366 (Dec 31), the window of Dec 31, 2002 includes Jan 1-5, 2003.

# So the pool for doy 1 should include dates from Dec 27, 1991 to Jan 6 of each year (or whatever).

# OK, my implementation should handle this correctly since I'm checking each date in the full window
# [1991-12-27, 2003-01-05] against each baseline date.

# Let me just verify the pool counts are right and then proceed.

# Check the pool for doy 59:
# Baseline dates with doy 59: Feb 28 of years 1992-2002 (11 dates)
# Windows: Feb 23 to Mar 4 of each year
# In non-leap years (1993,1994,1995,1997,1998,1999,2001,2002 - 8 years): Feb 23-28 + Mar 1-4 = 6+4 = 10 days
# In leap years (1992,1996,2000 - 3 years): Feb 23-29 + Mar 1-4 = 7+4 = 11 days
# Total: 8*10 + 3*11 = 80 + 33 = 113 days

# But wait, I need to check if any of these windows extend outside [1991-12-27, 2003-01-05].
# No, Feb 23-Mar 4 of any year 1992-2002 is well within that range.

# Pool for doy 1:
# Baseline dates with doy 1: Jan 1 of years 1992-2002 (11 dates)
# Windows: Dec 27 to Jan 6 of each year
# Dec 27, 1991 to Jan 6, 1992 (from Jan 1, 1992's window)
# Dec 27, 1992 to Jan 6, 1993 (from Jan 1, 1993's window)
# ...
# Dec 27, 2002 to Jan 6, 2003 (from Jan 1, 2003's window... but Jan 1, 2003 is not in the baseline range)

# Wait, baseline dates are 1992-01-01 to 2002-12-31.
# Jan 1, 1992 through Jan 1, 2002 are baseline dates with doy 1.
# Jan 1, 2003 is NOT a baseline date.
# So the windows for doy 1 are: Dec 27, 1991 to Jan 6, 1992 (11 days), ..., Dec 27, 2001 to Jan 6, 2002 (11 days).
# That's 11 windows × 11 days = 121 days.
# But Dec 27, 2002 to Jan 5, 2003? Those come from the window of Jan 1, 2003 which isn't a baseline date.
# Wait, but Dec 27, 2002 is within the window of Jan 1, 2002 (which is a baseline date with doy 1).
# Jan 1, 2002 + 5 days = Jan 6, 2002. So Dec 27, 2002 is 5 days after... no, it's 5 days before Jan 1, 2003.
# But we only have windows around baseline dates (1992-2002), so the last window for doy 1 is around Jan 1, 2002:
# Dec 27, 2001 to Jan 6, 2002.

# Hmm, but the instructions say "Windows near the ends of the baseline reach up to 5 days beyond it
# (1991-12-27 to 1991-12-31 and 2003-01-01 to 2003-01-05); include those days."

# This means: at the start of the baseline (Jan 1, 1992), the window extends 5 days back to Dec 27, 1991.
# At the end of the baseline (Dec 31, 2002), the window extends 5 days forward to Jan 5, 2003.

# So Dec 27-31, 1991 are included in the pool for doy 1 (via the window of Jan 1, 1992).
# And Jan 1-5, 2003 are included in the pool for doy 366 (via the window of Dec 31, 2002).

# But what about dates like Dec 27-31, 2002? Are they in pool 366?
# Dec 31, 2002 is a baseline date with doy 366. Its window is Dec 26, 2002 to Jan 5, 2003.
# So Dec 27-31, 2002 are in pool 366. ✓
# And Jan 1-5, 2003 are also in pool 366. ✓

# What about dates like Dec 26-31, 1991? Are they in any pool?
# They would be in the window of Jan 1, 1992's pool (doy 1), since Jan 1, 1992 - 5 days = Dec 27, 1991.
# So Dec 27-31, 1991 are in pool 1. ✓
# But Dec 26, 1991 is not in any pool (it's 6 days before Jan 1, 1992).

# OK, so my implementation seems correct. Let me check the actual pool sizes.

print("\nChecking pool sizes for key doys:")
for d in [1, 2, 58, 59, 61, 62, 182, 365, 366]:
    if d in pools:
        print(f"doy {d}: {pools[d].shape[0]} time points")
    else:
        print(f"doy {d}: empty/not found")
