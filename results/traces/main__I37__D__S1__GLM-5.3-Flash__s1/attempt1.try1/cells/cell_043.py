import os, json
import xarray as xr
import numpy as np

print(os.listdir('/work/output'))
ds = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
assert set(ds.dims) == {'time','lat','lon'}, ds.dims
assert ds['mhw'].dtype == np.uint8
assert ds['mhw'].dims == ('time','lat','lon')
assert ds.sizes['time'] == 92
assert ds.sizes['lat'] == 61 and ds.sizes['lon'] == 61
ds.close()

r = json.load(open('/work/output/report.json'))
assert set(r.keys()) == {'region','baseline_analysed','target_analysed','events','complete','caveats'}, r.keys()
assert r['complete'] is True and r['events'] == []
print("report fields OK:", {k: (v if k not in ('caveats',) else v[:40]+'...') for k,v in r.items()})
print("\nALL CHECKS PASSED")
