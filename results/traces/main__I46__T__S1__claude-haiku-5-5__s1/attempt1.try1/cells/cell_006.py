
import fsspec, datetime as dt
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z'
for s in ['sst_19921231.nc','sst_19920101.nc','sst_20130601.nc','sst_20130831.nc','sst_19911227.nc','sst_20030105.nc']:
    try:
        print(s, fs.exists(f'{base}/{s}'))
    except Exception as e: print(s,'ERR',e)
try:
    print(len(fs.ls(base, detail=False)))
except Exception as e: print(e)
