
import fsspec
import xarray as xr
import numpy as np

fs = fsspec.filesystem('onedata')

# Open a file to check the data structure
path = 'icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
f = fs.open(path, "rb")
ds = xr.open_dataset(f, engine="h5netcdf")

# Check lat/lon values in region
lats = ds.latitude.values
lons = ds.longitude.values

lat_mask = (lats >= 56.13) & (lats <= 57.33)
lon_mask = (lons >= 17.71) & (lons <= 18.91)

lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]

print(f"Latitude indices: {lat_idx[0]} to {lat_idx[-1]}, count={len(lat_idx)}")
print(f"Latitude values: {lats[lat_idx[0]]} to {lats[lat_idx[-1]]}")
print(f"Longitude indices: {lon_idx[0]} to {lon_idx[-1]}, count={len(lon_idx)}")
print(f"Longitude values: {lons[lon_idx[0]]} to {lons[lon_idx[-1]]}")

# Check the data
print(f"\nSST shape: {ds.analysed_sst.shape}")
print(f"SST min/max: {ds.analysed_sst.values.min()}, {ds.analysed_sst.values.max()}")
# Check for NaN
print(f"NaN count: {np.isnan(ds.analysed_sst.values).sum()}")

# Sample values in our region
print(f"\nSample region data:")
region_data = ds.analysed_sst.values[0, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1]
print(f"Shape: {region_data.shape}")
print(f"Finite: {np.isfinite(region_data).sum()}/{region_data.size}")
