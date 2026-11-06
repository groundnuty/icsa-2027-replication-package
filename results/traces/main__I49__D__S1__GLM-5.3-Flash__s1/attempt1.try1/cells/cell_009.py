import xarray as xr, numpy as np
for fn in ['sst_19911227.nc','sst_19920101.nc','sst_19960229.nc','sst_20190601.nc','sst_20190831.nc']:
    with xr.open_dataset(f'/work/nc/{fn}', engine='h5netcdf') as ds:
        tv = ds.time.values
        print(fn, "->", tv, "| str:", str(tv[0])[:10], "| decoded:", np.datetime_as_string(tv, unit='D'))
import datetime as dt
print("local tz offset check:", dt.datetime.now(), dt.datetime.utcnow())
