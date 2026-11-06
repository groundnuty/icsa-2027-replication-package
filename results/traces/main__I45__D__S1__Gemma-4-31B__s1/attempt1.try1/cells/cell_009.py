import xarray as xr
import fsspec

fs = fsspec.filesystem('onedata')
remote_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'
# If the file is already there, skip get
if not os.path.exists(local_path):
    fs.get(remote_path, local_path)

ds = xr.open_dataset(local_path, engine="h5netcdf")
lat_min, lat_max = 63.31, 64.51
lon_min, lon_max = 21.31, 22.51

# Slice region
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
print(f"Region coordinates:\n{ds_region.latitude}")
print(f"Region longitude:\n{ds_region.longitude}")
print(f"Shape: {ds_region.analysed_sst.shape}")
