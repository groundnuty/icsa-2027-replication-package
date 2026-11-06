
import json
r=json.load(open('/work/output/report.json'))
r['caveats']=r['caveats']+" The final event (2022-08-10 to 2022-08-31) reaches the end of the target window and may continue beyond it; it is truncated by design. Runtime warnings about all-NaN slices come from land cells only."
json.dump(r,open('/work/output/report.json','w'),indent=1)
import xarray as xr
m=xr.open_dataset('/work/output/mhw_mask.nc'); print(m.mhw.dims, m.mhw.shape, m.mhw.dtype, int(m.mhw.sum()))
print(os.path.exists('/work/output/report.json'))
