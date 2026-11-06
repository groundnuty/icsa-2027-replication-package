
import xarray as xr
import numpy as np
from datetime import date, timedelta

# Load one file to get lat/lon for the region
ds0 = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20130601.nc', engine='h5netcdf')
lat_all = ds0['latitude'].values
lon_all = ds0['longitude'].values

lat_mask = (lat_all >= 57.85) & (lat_all <= 59.05)
lon_mask = (lon_all >= 21.01) & (lon_all <= 22.21)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]
region_lat = lat_all[lat_idx]
region_lon = lon_all[lon_idx]
print("Region lat range:", region_lat[0], "to", region_lat[-1], "count:", len(region_lat))
print("Region lon range:", region_lon[0], "to", region_lon[-1], "count:", len(region_lon))
