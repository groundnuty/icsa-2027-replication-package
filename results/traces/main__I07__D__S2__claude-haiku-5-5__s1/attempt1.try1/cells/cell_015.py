
import xarray, json
o=xarray.open_dataset('/work/output/mhw_mask.nc')
print(o.mhw.dims, o.mhw.shape, o.mhw.dtype, int(o.mhw.sum()))
print(json.load(open('/work/output/report.json')))
