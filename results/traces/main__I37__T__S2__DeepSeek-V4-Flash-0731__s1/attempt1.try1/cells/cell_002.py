
import fsspec
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
# List contents
print(fs.ls('icsa2027_data_20261101T090944Z'))
print(fs.ls('icsa2027_data_20261101T090944Z/s2z'))
