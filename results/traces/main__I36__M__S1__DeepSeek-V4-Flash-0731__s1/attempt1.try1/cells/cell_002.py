
import xarray as xr
import os

files = sorted(os.listdir('/data/icsa2027_data_20261101T090944Z/s1z'))
print(f"Number of files: {len(files)}")
print(f"First few: {files[:3]}")
print(f"Last few: {files[-3:]}")

# Open one file to understand structure
ds = xr.open_dataset(os.path.join('/data/icsa2027_data_20261101T090944Z/s1z', files[0]), engine='h5netcdf')
print(ds)
print(ds.variables)
