import fsspec
import xarray as xr

fs = fsspec.filesystem('onedata')

# List the directory
print(fs.ls('icsa2027_data_20261101T090944Z/s1z'))
