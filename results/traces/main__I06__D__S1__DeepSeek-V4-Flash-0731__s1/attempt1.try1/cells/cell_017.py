
import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

lat_min, lat_max = 54.45, 55.65
lon_min, lon_max = 16.05, 17.25
lat = ds.latitude.values
lon = ds.longitude.values
lat_idx = np.where((lat >= lat_min) & (lat <= lat_max))[0]
lon_idx = np.where((lon >= lon_min) & (lon <= lon_max))[0]

# Check one day of data in the region
time = ds.time.values
t_idx = 3647  # first baseline day
sst_slice = ds.analysed_sst[t_idx, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1].values
print(f"SST slice shape: {sst_slice.shape}")
print(f"Min: {np.nanmin(sst_slice):.4f}, Max: {np.nanmax(sst_slice):.4f}")
print(f"NaN count: {np.isnan(sst_slice).sum()}")
print(f"Sample values: {sst_slice.flatten()[:10]}")

# Check what happens at a specific location
print(f"\nFirst few lat/lon values:")
print(f"lat[0]: {lat[lat_idx[0]]}, lat[1]: {lat[lat_idx[0]+1]}")
print(f"lon[0]: {lon[lon_idx[0]]}, lon[1]: {lon[lon_idx[0]+1]}")

# Check units from attributes
print(f"\nAttributes of analysed_sst:")
print(ds.analysed_sst.attrs)
