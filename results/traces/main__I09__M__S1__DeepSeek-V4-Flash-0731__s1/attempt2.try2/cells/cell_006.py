
import xarray as xr
import numpy as np

# Check file size for one file
f = '/data/icsa2027_data_20261101T090944Z/s1z/sst_20220601.nc'
ds = xr.open_dataset(f, engine='h5netcdf')
print(f"File size: {ds.analysed_sst.values.nbytes / 1e6:.1f} MB")

# Check the region data
lats = ds.latitude.values
lons = ds.longitude.values
lat_idx = np.where((lats >= 54.81) & (lats <= 56.01))[0]
lon_idx = np.where((lons >= 19.61) & (lons <= 20.81))[0]

sst_region = ds.analysed_sst[0, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1].values
print(f"Region shape: {sst_region.shape}")
print(f"NaN count in region: {np.isnan(sst_region).sum()}")
print(f"Total cells: {sst_region.size}")

# Check if there's a fill value or what NaN means
print(f"Some values: {sst_region.flatten()[:20]}")

# Check land mask - what values does land have?
print(f"Min: {np.nanmin(sst_region)}, Max: {np.nanmax(sst_region)}")
