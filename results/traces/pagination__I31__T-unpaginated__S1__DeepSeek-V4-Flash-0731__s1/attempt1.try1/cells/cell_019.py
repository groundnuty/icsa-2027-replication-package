
import fsspec
import xarray as xr
import numpy as np
import datetime as dt

fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'

lat_start, lat_end = 260, 319
lon_start, lon_end = 485, 544

# Load a single baseline file for a summer day
# doy for July 1 = month_offsets[7] + 1 = 182 + 1 = 183
# Let me check what dates contribute to doy 183 (July 1)

month_offsets = {1: 0, 2: 31, 3: 60, 4: 91, 5: 121, 6: 152, 7: 182, 8: 213, 9: 244, 10: 274, 11: 305, 12: 335}
def date_to_doy(y, m, d):
    return month_offsets[m] + d

# For doy 183 (July 1), the pool includes dates within ±5 days of July 1 in 1992-2002
# Plus Feb 29 values for nearby doy (but that doesn't apply here)

# Let's load data for July 1, 1992 and check a specific cell
# First, find a sea cell by checking a target file
f = fs.open(f'{base_path}/sst_20170615.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
sst_target = ds.analysed_sst.values[0, lat_start:lat_end+1, lon_start:lon_end+1]
ds.close()

# Find a sea cell
for i in range(60):
    for j in range(60):
        if np.isfinite(sst_target[i, j]):
            print(f"Sea cell at ({i},{j}): {sst_target[i,j]}")
            sea_cell = (i, j)
            break
    else:
        continue
    break

# Load all dates around July 1 for all baseline years
print(f"\nExamining cell ({sea_cell[0]},{sea_cell[1]})")
print(f"Target SST on 2017-06-15: {sst_target[sea_cell[0], sea_cell[1]]}")

# Load baseline values around July 1 for all years
for year in range(1992, 2003):
    for offset in range(-5, 6):
        d = dt.date(year, 7, 1) + dt.timedelta(days=offset)
        fname = f"sst_{d.year:04d}{d.month:02d}{d.day:02d}.nc"
        f = fs.open(f'{base_path}/{fname}', 'rb')
        ds = xr.open_dataset(f, engine='h5netcdf')
        val = ds.analysed_sst.values[0, lat_start+sea_cell[0], lon_start+sea_cell[1]]
        ds.close()
        if offset == 0:
            print(f"  {year}-07-01: {val:.2f}")
        elif offset in [-5, 5]:
            print(f"  {d}: {val:.2f}")
