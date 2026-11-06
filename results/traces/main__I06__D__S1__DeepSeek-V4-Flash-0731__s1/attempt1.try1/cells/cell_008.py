
import fsspec
fs = fsspec.filesystem('onedata')
# Download the s2 file
fs.get('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', '/work/sst_s2.nc')
print("Downloaded s2 file")
