import xarray as xr
import os

# Load the mask and coordinates again
# Or just reopen the dataset and rename
mhw_ds = xr.open_dataset("output/mhw_mask.nc")
mhw_ds = mhw_ds.rename({"latitude": "lat", "longitude": "lon"})
mhw_ds.to_netcdf("output/mhw_mask.nc")
mhw_ds.close()
print("Dimensions renamed to lat and lon.")
