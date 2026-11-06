import os
for p in ('output/mhw_mask.nc', 'output/report.json'):
    print(p, os.path.getsize(p), "bytes, exists:", os.path.exists(p))
import xarray as xr, json
d = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("dims:", dict(d.sizes), "| mhw dtype:", d['mhw'].dtype, "| ones:", int(d['mhw'].values.sum()))
r = json.load(open('output/report.json'))
print("report keys:", sorted(r.keys()))
print("events:", r['events'], "| complete:", r['complete'])
d.close()
