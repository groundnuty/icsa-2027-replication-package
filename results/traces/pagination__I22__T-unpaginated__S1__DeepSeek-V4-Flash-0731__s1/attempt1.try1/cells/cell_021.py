
import fsspec
import xarray as xr
import numpy as np
import datetime

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

lat_idx = np.arange(196, 256)
lon_idx = np.arange(485, 545)

# Load reference file for coordinates
with fs.open(f'{base}/sst_20040601.nc', 'rb') as fh:
    ds = xr.open_dataset(fh, engine='h5netcdf')
    lat_full = ds['latitude'].values
    lon_full = ds['longitude'].values
    ds.close()

region_lat = lat_full[lat_idx]
region_lon = lon_full[lon_idx]

print(f'Region lat: {region_lat[0]:.6f} to {region_lat[-1]:.6f}, count={len(region_lat)}')
print(f'Region lon: {region_lon[0]:.6f} to {region_lon[-1]:.6f}, count={len(region_lon)}')
print(f'Data type: {region_lat.dtype}')

# Target dates
target_dates = []
d = datetime.date(2004, 6, 1)
while d <= datetime.date(2004, 8, 31):
    target_dates.append(d)
    d += datetime.timedelta(days=1)
print(f'Target dates: {len(target_dates)}')
