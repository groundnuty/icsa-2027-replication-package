
import fsspec
fs = fsspec.filesystem('onedata')
# Explore the dataset
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
print(fs.ls('/'))
