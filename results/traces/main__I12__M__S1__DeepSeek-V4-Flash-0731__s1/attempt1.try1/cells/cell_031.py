
import xarray as xr
import numpy as np
from datetime import date, timedelta
import os, json

# =====================================================
# Load all intermediate data
# =====================================================
per_cell_mhw = np.load('/tmp/per_cell_mhw.npy')  # shape (92, 60, 60)

# Get region lat/lon from original dataset
ds0 = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20090601.nc', engine='h5netcdf')
lats_full = ds0.latitude.values
lons_full = ds0.longitude.values
ds0.close()

lat_min, lat_max = 56.09, 57.29
lon_min, lon_max = 10.55, 11.75

lat_mask = (lats_full >= lat_min) & (lats_full <= lat_max)
lon_mask = (lons_full >= lon_min) & (lons_full <= lon_max)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]
lat_start, lat_end = lat_idx[0], lat_idx[-1] + 1
lon_start, lon_end = lon_idx[0], lon_idx[-1] + 1

region_lats = lats_full[lat_start:lat_end]
region_lons = lons_full[lon_start:lon_end]

# Target dates
target_dates = []
d = date(2009, 6, 1)
while d <= date(2009, 8, 31):
    target_dates.append(d)
    d += timedelta(days=1)

# Get time coordinate values from dataset files
data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'
time_coords = []
for td in target_dates:
    fname = f'sst_{td.strftime("%Y%m%d")}.nc'
    ds = xr.open_dataset(os.path.join(data_dir, fname), engine='h5netcdf')
    time_coords.append(ds.time.values[0])
    ds.close()
time_coords = np.array(time_coords)

# =====================================================
# Create output NetCDF
# =====================================================
# mhw mask: 1 where cell is inside a per-cell MHW on that day, 0 otherwise
mhw_mask = per_cell_mhw.astype(np.uint8)

# Create xarray dataset
ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_mask),
    },
    coords={
        'time': time_coords,
        'lat': region_lats,
        'lon': region_lons,
    }
)

# Add attributes
ds_out.mhw.attrs['long_name'] = 'Marine heatwave mask'
ds_out.mhw.attrs['units'] = '1 = in MHW, 0 = not in MHW'

ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Written output/mhw_mask.nc")
print(f"  Shape: {ds_out.mhw.shape}")
print(f"  dtype: {ds_out.mhw.dtype}")
print(f"  time: {time_coords[0]} to {time_coords[-1]}")
print(f"  lat: {region_lats[0]} to {region_lats[-1]}")
print(f"  lon: {region_lons[0]} to {region_lons[-1]}")
print(f"  mhw sum: {mhw_mask.sum()}")
