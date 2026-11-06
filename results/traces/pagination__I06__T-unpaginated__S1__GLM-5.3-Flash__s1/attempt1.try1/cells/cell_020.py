import os, json
import numpy as np, xarray as xr

print("files:", os.listdir('output'), "| sizes:", {f: os.path.getsize(f'output/{f}') for f in os.listdir('output')})

ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
m = ds['mhw']
print("dims:", dict(ds.sizes), "dtype:", m.dtype)
print("mhw sum:", int(m.values.sum()), "unique:", np.unique(m.values))
# per-day active count summary
act = m.values.any(axis=(1,2))
print("active days:", int(act.sum()))
import datetime as dt
times = ds['time'].values.astype('datetime64[D]')
for t in np.flatnonzero(act):
    print("  ", str(times[t]), "cells:", int(m.values[t].sum()))
ds.close()

r = json.load(open('output/report.json'))
print("report:", json.dumps(r))
assert isinstance(r['region']['lat_min'], float) and isinstance(r['complete'], bool)
assert r['events'] == [{"onset":"2012-06-11","end":"2012-06-16"},{"onset":"2012-07-25","end":"2012-07-29"}]
print("FINAL CHECK PASSED")
