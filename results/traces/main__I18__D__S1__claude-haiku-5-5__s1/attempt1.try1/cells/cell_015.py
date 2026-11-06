import numpy as np, xarray as xr, json, os
os.makedirs('/work/output',exist_ok=True)
r=np.load('/work/result.npz')
mhw=r['mhw'].astype(np.uint8); tdays=r['tdays']; LAT=r['lat']; LON=r['lon']
ds=xr.Dataset({'mhw':(('time','lat','lon'),mhw)},
              coords={'time':('time',np.array(tdays,dtype='datetime64[ns]')),'lat':('lat',LAT),'lon':('lon',LON)})
ds.to_netcdf('/work/output/mhw_mask.nc', format='NETCDF4', engine='h5netcdf')
ev=json.load(open('/work/events.json'))['events']
rep={'region':{'lat_min':57.13,'lat_max':58.33,'lon_min':22.79,'lon_max':23.99},
     'baseline_analysed':{'start':'1992-01-01','end':'2002-12-31'},
     'target_analysed':{'start':'2010-06-01','end':'2010-08-31'},
     'events':[{'onset':a,'end':b} for a,b in ev],
     'complete':True,
     'caveats':('Raw daily files beyond the 1000-entry directory listing cap were fetched by direct path; all 4120 needed days were used. '
                'Sea cells = 3301 of 3600 region cells (finite on all target days). Per-cell MHW gap joining: consecutive >=5-day hot runs separated by 1-2 days (all non-MHW) were merged. '
                'Smoothing uses plain mean (no NaN handling); no sea cell had NaN thresholds. Mask lists all 92 target days; land cells are 0.')}
json.dump(rep,open('/work/output/report.json','w'),indent=2)
print(open('/work/output/report.json').read()); print(xr.open_dataset('/work/output/mhw_mask.nc',engine='h5netcdf'))