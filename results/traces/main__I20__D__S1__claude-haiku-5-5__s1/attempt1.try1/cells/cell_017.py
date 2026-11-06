import xarray as xr, json
x=xr.open_dataset('/work/output/mhw_mask.nc')
print(x)
print(x.mhw.dtype, int(x.mhw.sum()))
print(json.load(open('/work/output/report.json'))['events'])