
import fsspec
import xarray as xr
import numpy as np
import datetime as dt
import time

fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'

lat_start, lat_end = 260, 319
lon_start, lon_end = 485, 544
n_lat, n_lon = 60, 60

month_offsets = {1: 0, 2: 31, 3: 60, 4: 91, 5: 121, 6: 152, 7: 182, 8: 213, 9: 244, 10: 274, 11: 305, 12: 335}
def date_to_doy(y, m, d):
    return month_offsets[m] + d

# Load a specific target date to find a sea cell
f = fs.open(f'{base_path}/sst_20170601.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
sst_jun1 = ds.analysed_sst.values[0, lat_start:lat_end+1, lon_start:lon_end+1]
ds.close()

# Find a sea cell
sea_cells_found = []
for i in range(n_lat):
    for j in range(n_lon):
        if np.isfinite(sst_jun1[i, j]):
            sea_cells_found.append((i, j))
            if len(sea_cells_found) >= 5:
                break
    if len(sea_cells_found) >= 5:
        break

print("Sample sea cells:", sea_cells_found)

# Take cell (0,0) and compute its threshold for doy 183 (July 1)
# doy 183: baseline dates July 1, 1992-2002
# Pool: June 26 - July 6 for each year

cell = sea_cells_found[0]
print(f"\nAnalyzing cell {cell}")

# Load pool values for doy 183 for this cell
pool_vals = []
for year in range(1992, 2003):
    for offset in range(-5, 6):
        d = dt.date(year, 7, 1) + dt.timedelta(days=offset)
        fname = f"sst_{d.year:04d}{d.month:02d}{d.day:02d}.nc"
        f = fs.open(f'{base_path}/{fname}', 'rb')
        ds = xr.open_dataset(f, engine='h5netcdf')
        val = ds.analysed_sst.values[0, lat_start+cell[0], lon_start+cell[1]]
        ds.close()
        pool_vals.append(float(val))

pool_vals = np.array(pool_vals)
valid = pool_vals[~np.isnan(pool_vals)]
print(f"Pool values for doy 183: {len(valid)} valid out of {len(pool_vals)}")
print(f"Pool values: {valid}")
print(f"Mean: {np.mean(valid):.2f}")
print(f"90th percentile (hazen): {np.percentile(valid, 90, method='hazen'):.2f}")
print(f"Target SST on 2017-06-01: {sst_jun1[cell[0], cell[1]]}")
