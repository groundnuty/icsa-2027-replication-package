
import xarray as xr, numpy as np, json
m=xr.open_dataset('/work/output/mhw_mask.nc')
print(m.mhw.dims, m.mhw.shape, m.mhw.dtype)
c=m.mhw.sum(('lat','lon')).to_pandas()
print(c[c>0].to_string())
print(json.load(open('/work/output/report.json'))['events'])