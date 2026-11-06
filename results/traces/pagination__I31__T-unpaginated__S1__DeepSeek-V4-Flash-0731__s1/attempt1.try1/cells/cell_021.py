
import fsspec
import xarray as xr
import numpy as np
import datetime as dt

fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'

lat_start, lat_end = 260, 319
lon_start, lon_end = 485, 544

month_offsets = {1: 0, 2: 31, 3: 60, 4: 91, 5: 121, 6: 152, 7: 182, 8: 213, 9: 244, 10: 274, 11: 305, 12: 335}
def date_to_doy(y, m, d):
    return month_offsets[m] + d

# Load target data for cell (0,0) for the full target period
cell = (0, 0)
target_vals = []
target_dates = []

d = dt.date(2017, 6, 1)
while d <= dt.date(2017, 8, 31):
    fname = f"sst_{d.year:04d}{d.month:02d}{d.day:02d}.nc"
    f = fs.open(f'{base_path}/{fname}', 'rb')
    ds = xr.open_dataset(f, engine='h5netcdf')
    val = float(ds.analysed_sst.values[0, lat_start+cell[0], lon_start+cell[1]])
    ds.close()
    target_vals.append(val)
    target_dates.append(d)
    d += dt.timedelta(days=1)

print(f"Target SST for cell {cell} over the summer:")
for i, (dd, v) in enumerate(zip(target_dates, target_vals)):
    doy = date_to_doy(dd.year, dd.month, dd.day)
    if (i % 10) == 0:
        print(f"  {dd} (doy {doy}): {v:.2f}")

print(f"\nTarget SST min: {min(target_vals):.2f}")
print(f"Target SST max: {max(target_vals):.2f}")
