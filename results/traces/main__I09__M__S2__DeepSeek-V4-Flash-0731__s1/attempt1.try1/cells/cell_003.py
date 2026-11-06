
import xarray as xr
import numpy as np

path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(path, engine='h5netcdf')

lat_min, lat_max = 54.81, 56.01
lon_min, lon_max = 19.61, 20.81

# Select region
lat_sel = ds.latitude.values
lon_sel = ds.longitude.values
lat_idx = np.where((lat_sel >= lat_min) & (lat_sel <= lat_max))[0]
lon_idx = np.where((lon_sel >= lon_min) & (lon_sel <= lon_max))[0]

lat_vals = lat_sel[lat_idx]
lon_vals = lon_sel[lon_idx]
print("n_lat:", len(lat_idx), "n_lon:", len(lon_idx))

# Load the region data for all time
sst_region = ds['analysed_sst'][:, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1]
print("sst_region shape:", sst_region.shape)

# Check time
time_vals = ds.time.values
print("time dtype:", time_vals.dtype)
print("first/last:", time_vals[0], time_vals[-1])
