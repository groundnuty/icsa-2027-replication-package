import os, json, numpy as np, pandas as pd, xarray as xr
os.makedirs('output',exist_ok=True)
ds_out=xr.Dataset({'mhw':(('time','lat','lon'),mhw_cell.astype(np.uint8))},
    coords={'time':tdays.values,'lat':lat,'lon':lon})
ds_out['mhw'].attrs={'long_name':'marine heatwave mask'}
ds_out.to_netcdf('output/mhw_mask.nc',engine='h5netcdf')
report={"region":{"lat_min":64.39,"lat_max":65.59,"lon_min":23.41,"lon_max":24.61},
 "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
 "target_analysed":{"start":"2019-06-01","end":"2019-08-31"},
 "events":events,"complete":True,
 "caveats":"Region grid cells analysed: lat 64.40-65.58, lon 23.42-24.60 (60x60; 3311 cells are sea over the whole target period, others written as 0). Baseline extension days 1991-12-27..31 and 2003-01-01..05 used in pools as specified. Thresholds computed in float64 from float32 SST values as stored (kelvin). Two regional events found."}
json.dump(report,open('output/report.json','w'),indent=1)
chk=xr.open_dataset('output/mhw_mask.nc'); print(chk.mhw.dims, chk.mhw.shape, chk.mhw.dtype, int(chk.mhw.sum())); print(report['events'])
