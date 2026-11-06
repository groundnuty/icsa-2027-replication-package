import xarray as xr
import fsspec

fs = fsspec.filesystem('onedata')
remote_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'
if not os.path.exists(local_path):
    fs.get(remote_path, local_path)

ds = xr.open_dataset(local_path, engine="h5netcdf")
print(f"Lat range: {ds.latitude.min().values} to {ds.latitude.max().values}")
print(f"Lon range: {ds.longitude.min().values} to {ds.longitude.max().values}")

lat_min, lat_max = 57.33, 58.53
lon_min, lon_max = 9.03, 10.23

lat_slice = ds.latitude.sel(latitude=slice(lat_min, lat_max))
lon_slice = ds.longitude.sel(longitude=slice(lon_min, lon_max))

print(f"Lat slice: {len(lat_slice)} points")
print(f"Lon slice: {len(lon_slice)} points")
