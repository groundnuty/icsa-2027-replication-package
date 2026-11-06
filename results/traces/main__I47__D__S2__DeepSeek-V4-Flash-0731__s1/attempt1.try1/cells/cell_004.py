
import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

lat = ds.latitude.values
lon = ds.longitude.values
print("lat range", lat.min(), lat.max(), "n=", len(lat))
print("lon range", lon.min(), lon.max(), "n=", len(lon))
print("time range", ds.time.values[0], ds.time.values[-1], "n=", len(ds.time))

# find indices for region
lat_idx = [i for i,v in enumerate(lat) if 64.39 <= v <= 65.59]
lon_idx = [i for i,v in enumerate(lon) if 23.41 <= v <= 24.61]
print("lat idx", lat_idx[0], lat_idx[-1], "values", lat[lat_idx[0]], lat[lat_idx[-1]])
print("lon idx", lon_idx[0], lon_idx[-1], "values", lon[lon_idx[0]], lon[lon_idx[-1]])
