import xarray as xr, json
import numpy as np
fs = __import__('fsspec').filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
src = xr.open_dataset(f, engine='h5netcdf')
ds = xr.open_dataset('/work/output/mhw_mask.nc')
tt = src.time.values
i0 = int(np.searchsorted(tt, np.datetime64('2017-06-01')))
i1 = int(np.searchsorted(tt, np.datetime64('2017-08-31'))) + 1
print("time coords match source:", np.array_equal(ds.time.values, tt[i0:i1]), "range:", str(tt[i0])[:10], "..", str(tt[i1-1])[:10])

rep = json.load(open('/work/output/report.json'))
print(json.dumps(rep, indent=1))
print("fields:", sorted(rep.keys()))
print("events type:", type(rep['events']), "complete:", rep['complete'], "caveats len:", len(rep['caveats']))
