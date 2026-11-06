
import json, xarray as xr
rep=json.load(open('/work/output/report.json'))
rep['region']={'lat_min':63.31,'lat_max':64.51,'lon_min':21.31,'lon_max':22.51}
rep['caveats']=rep['caveats']+" Region bounds reported as requested; the native grid cells inside are 63.32-64.50 N, 21.32-22.50 E."
json.dump(rep,open('/work/output/report.json','w'),indent=2)
m=xr.open_dataset('/work/output/mhw_mask.nc')
print(m.mhw.dims, m.mhw.dtype, m.mhw.shape, int(m.mhw.sum()), str(m.time.values[0])[:10], str(m.time.values[-1])[:10])
print(rep['events'])
