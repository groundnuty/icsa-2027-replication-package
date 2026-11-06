for p in ['sst_20080601.nc','sst_19920101.nc','sst_19911231.nc','sst_20080831.nc','sst_20030105.nc']:
    try:
        with fs.open('icsa2027_data_20261101T090944Z/s1z/'+p,'rb') as f: print(p,'ok',len(f.read()))
    except Exception as e: print(p,'ERR',repr(e)[:200])
# also try listing with detail / subdirs
print(fs.ls('icsa2027_data_20261101T090944Z', detail=False)[:20])