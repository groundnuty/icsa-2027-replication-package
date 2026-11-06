import xarray as xr, json
d=xr.open_dataset('/work/output/mhw_mask.nc'); print(d); print(d.mhw.dtype)
print(json.load(open('/work/output/report.json')))