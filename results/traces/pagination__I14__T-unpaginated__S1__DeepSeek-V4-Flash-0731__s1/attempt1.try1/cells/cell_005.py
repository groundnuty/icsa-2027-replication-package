
import fsspec
import xarray as xr
import numpy as np

fs = fsspec.filesystem('onedata')

# Check the region data more carefully
path = 'icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
f = fs.open(path, "rb")
ds = xr.open_dataset(f, engine="h5netcdf")

# Check data in region for a non-winter month
region_data = ds.analysed_sst.values[0, 132:192, 436:496]
# Find finite values
finite_mask = np.isfinite(region_data)
finite_vals = region_data[finite_mask]
print(f"Finite values in region: {finite_vals[:10]}")
print(f"Mean: {finite_vals.mean()}")

# Check the attribute for units
print(ds.analysed_sst.attrs)
