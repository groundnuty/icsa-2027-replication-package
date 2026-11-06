import xarray as xr
import fsspec

fs = fsspec.filesystem('onedata')
sample_file = 'icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
with fs.open(sample_file, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    lat = ds.latitude
    lon = ds.longitude
    
    lat_min, lat_max = 56.63, 57.83
    lon_min, lon_max = 20.23, 21.43
    
    lat_mask = (lat >= lat_min) & (lat <= lat_max)
    lon_mask = (lon >= lon_min) & (lon <= lon_max)
    
    print(f"Latitude range: {lat.min().values} to {lat.max().values}")
    print(f"Longitude range: {lon.min().values} to {lon.max().values}")
    print(f"Lat indices: {lat_mask.argmin().values} to {lat_mask.argmax().values}") # Not quite correct, but let's see
    print(f"Lat selection: {lat[lat_mask].values}")
    print(f"Lon selection: {lon[lon_mask].values}")
