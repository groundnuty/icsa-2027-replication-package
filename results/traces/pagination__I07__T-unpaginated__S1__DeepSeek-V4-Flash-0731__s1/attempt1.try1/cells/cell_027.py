
import fsspec
import xarray as xr
import numpy as np

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# Get coordinate values from the dataset
with fs.open(f'{base}/sst_20210601.nc', 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    lats = ds.latitude.values
    lons = ds.longitude.values
    times = ds.time.values

# Region indices
lat_start, lat_end = 48, 108  # inclusive 48-107
lon_start, lon_end = 353, 413  # inclusive 353-412

region_lats = lats[lat_start:lat_end]
region_lons = lons[lon_start:lon_end]
print(f"Region lats: {len(region_lats)}, first={region_lats[0]}, last={region_lats[-1]}")
print(f"Region lons: {len(region_lons)}, first={region_lons[0]}, last={region_lons[-1]}")
