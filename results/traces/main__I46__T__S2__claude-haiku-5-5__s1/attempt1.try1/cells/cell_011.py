
import shutil,os
os.makedirs('/work/output',exist_ok=True)
for fn in ['mhw_mask.nc','report.json']:
    shutil.copy('/tmp/w/output/'+fn,'/work/output/'+fn)
import xarray as xr, json
m=xr.open_dataset('/work/output/mhw_mask.nc'); print(m.mhw.dtype, dict(m.mhw.sizes))
print(json.load(open('/work/output/report.json'))['events'])
