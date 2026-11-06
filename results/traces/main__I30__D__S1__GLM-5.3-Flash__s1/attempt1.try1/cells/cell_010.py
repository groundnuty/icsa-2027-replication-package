import fsspec, os
fs = fsspec.filesystem('onedata')
fs.get('icsa2027_data_20261101T090944Z/s1z/sst_20100601.nc', '/work/daily_20100601.nc')
fs.get('icsa2027_data_20261101T090944Z/s1z/sst_19920601.nc', '/work/daily_19920601.nc')
print('ok', os.path.getsize('/work/daily_20100601.nc'), os.path.getsize('/work/daily_19920601.nc'))
