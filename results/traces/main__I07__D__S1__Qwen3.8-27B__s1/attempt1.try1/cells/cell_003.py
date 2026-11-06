import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
# check specific 2021 files directly
for f in ['sst_20210601.nc', 'sst_20210831.nc', 'sst_19920101.nc', 'sst_20021231.nc', 'sst_20030105.nc', 'sst_19911227.nc']:
    p = f'{base}/{f}'
    try:
        info = fs.info(p)
        print(f, "EXISTS", info.get('size'))
    except Exception as e:
        print(f, "MISSING:", type(e).__name__)
# also check parent dir listing length
parent = 'icsa2027_data_20261101T090944Z'
try:
    print("parent entries:", fs.ls(parent))
except Exception as e:
    print("parent ERR", e)
