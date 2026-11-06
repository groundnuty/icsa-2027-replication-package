
import xarray as xr, json, os
os.makedirs('output',exist_ok=True)
ds=xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype(np.uint8))},
              coords={'time':('time',np.array([np.datetime64(d) for d in tdates],dtype='datetime64[ns]')),
                      'lat':('lat',rlat.astype(np.float32)),'lon':('lon',rlon.astype(np.float32))})
ds['mhw'].encoding={'dtype':'uint8'}
ds.to_netcdf('output/mhw_mask.nc')
rep={'region':{'lat_min':56.13,'lat_max':57.33,'lon_min':17.71,'lon_max':18.91},
     'baseline_analysed':{'start':'1992-01-01','end':'2002-12-31'},
     'target_analysed':{'start':'2019-06-01','end':'2019-08-31'},
     'events':events,'complete':True,
     'caveats':'Pipeline run on cached region subset (lat 56.14-57.32, lon 17.72-18.90 grid cells). Only 3300 of 3600 region cells are sea cells (finite all target days); others excluded and set to 0. Per-cell MHW analysis restricted to target period. Day 60 threshold/climatology set to mean of days 59 and 61 before smoothing. SST used as stored (float32 Kelvin, cast to float64).'}
json.dump(rep,open('output/report.json','w'),indent=2)
chk=xr.open_dataset('output/mhw_mask.nc'); print(chk.mhw.dtype, chk.mhw.shape, int(chk.mhw.sum()))
print(open('output/report.json').read()[:600])
