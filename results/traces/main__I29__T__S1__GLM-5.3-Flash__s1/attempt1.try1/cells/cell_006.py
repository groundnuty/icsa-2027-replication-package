import fsspec
fs = fsspec.filesystem('onedata')
for p in ['icsa2027_data_20261101T090944Z/s1z/sst_19920601.nc',
          'icsa2027_data_20261101T090944Z/s1z/sst_19921231.nc',
          'icsa2027_data_20261101T090944Z/s1z/sst_20150601.nc',
          'icsa2027_data_20261101T090944Z/s1z/sst_20150831.nc',
          'icsa2027_data_20261101T090944Z/s1z/sst_19911227.nc',
          'icsa2027_data_20261101T090944Z/s1z/sst_20030105.nc']:
    try:
        print(p, fs.exists(p))
    except Exception as e:
        print(p, 'ERR', e)
