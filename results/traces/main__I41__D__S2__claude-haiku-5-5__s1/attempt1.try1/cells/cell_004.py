
import fsspec
fs = fsspec.filesystem('onedata')
print(fs.info('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'))
