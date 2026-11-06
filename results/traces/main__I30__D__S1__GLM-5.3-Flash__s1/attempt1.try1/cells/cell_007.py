import fsspec
fs = fsspec.filesystem('onedata')
# does s1z contain later dates?
for f in ['sst_19920601.nc','sst_20100601.nc','sst_20231231.nc','sst_19840927.nc']:
    p = f'icsa2027_data_20261101T090944Z/s1z/{f}'
    try:
        print(f, fs.exists(p))
    except Exception as e:
        print(f, 'ERR', e)
