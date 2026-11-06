
import json, xarray as xr
rep=json.load(open('output/report.json'))
rep['caveats']+=" The single event starts on 2013-06-01, the first target day, so it may have begun earlier (left-censored by the target window; pre-window SST was not used)."
json.dump(rep,open('output/report.json','w'),indent=2)
ds=xr.open_dataset('output/mhw_mask.nc')
print(ds.mhw.dtype, ds.mhw.dims, ds.mhw.shape, int(ds.mhw.sum()))
print(json.load(open('output/report.json'))['events'])
