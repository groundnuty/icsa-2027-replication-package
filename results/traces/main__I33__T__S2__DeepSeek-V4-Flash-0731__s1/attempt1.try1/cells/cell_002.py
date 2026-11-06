
import fsspec
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
# get file attributes
attrs = fs.info(path)
print(attrs)
