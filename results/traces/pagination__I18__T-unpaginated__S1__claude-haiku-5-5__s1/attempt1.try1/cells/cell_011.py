import os, json, numpy as np, xarray as xr, pandas as pd
os.makedirs('output',exist_ok=True)
da=xr.DataArray(mhw.astype(np.uint8),dims=('time','lat','lon'),
    coords={'time':pd.to_datetime([d.isoformat() for d in tdates]),'lat':latv,'lon':lonv},name='mhw')
da.to_dataset().to_netcdf('output/mhw_mask.nc')
rep={'region':{'lat_min':57.13,'lat_max':58.33,'lon_min':22.79,'lon_max':23.99},
     'baseline_analysed':{'start':'1992-01-01','end':'2002-12-31'},
     'target_analysed':{'start':'2010-06-01','end':'2010-08-31'},
     'events':events,'complete':True,
     'caveats':'Pools built from SST on 1991-12-27..2003-01-05 with +-5 day windows. Day 60 threshold/climatology = mean of days 59 and 61 before smoothing. Grid cells are 60x60 within bounds (lat 57.14-58.32, lon 22.80-23.98). Per-cell MHW joins require all gap days non-hot. Land and cells not finite on every target day are never sea cells and are 0 in the mask.'}
json.dump(rep,open('output/report.json','w'),indent=2)
chk=xr.open_dataset('output/mhw_mask.nc'); print(chk.mhw.dims, chk.mhw.shape, chk.mhw.dtype, int(chk.mhw.sum()))
print(open('output/report.json').read()[:400])