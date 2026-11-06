
import fsspec
fs = fsspec.filesystem('onedata')
# Download one s1z file
fs.get('icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc', '/work/sst_19820101.nc')
print("Downloaded")
