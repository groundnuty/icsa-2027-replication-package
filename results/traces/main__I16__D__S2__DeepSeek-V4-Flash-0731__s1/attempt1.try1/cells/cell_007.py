
import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

lat = ds.latitude.values
lon = ds.longitude.values
lat_idx = np.where((lat >= 56.63) & (lat <= 57.83))[0]
lon_idx = np.where((lon >= 20.23) & (lon <= 21.43))[0]

time = ds.time.values
b_start = np.where(time >= np.datetime64('1991-12-27'))[0][0]
b_end = np.where(time <= np.datetime64('2003-01-05'))[0][-1]
t_start = np.where(time >= np.datetime64('2008-06-01'))[0][0]
t_end = np.where(time <= np.datetime64('2008-08-31'))[0][-1]

# Load region data
region = ds['analysed_sst'].isel(time=slice(b_start, b_end+1), 
                                  latitude=lat_idx, longitude=lon_idx).load()
print("baseline region data shape:", region.shape)
print("baseline time range:", region.time.values[0], region.time.values[-1])

region_target = ds['analysed_sst'].isel(time=slice(t_start, t_end+1),
                                        latitude=lat_idx, longitude=lon_idx).load()
print("target region data shape:", region_target.shape)
print("target time range:", region_target.time.values[0], region_target.time.values[-1])
