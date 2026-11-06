
import xarray as xr, json
m=xr.open_dataset('output/mhw_mask.nc'); print(m); print(m.mhw.dtype, int(m.mhw.sum()))
print(json.load(open('output/report.json'))['events'])
