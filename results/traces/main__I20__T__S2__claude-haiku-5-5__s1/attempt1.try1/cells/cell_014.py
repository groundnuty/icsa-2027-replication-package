
import subprocess
wr = r'''
import numpy as np, pandas as pd, json, os, xarray as xr
mhw=np.load('/tmp/w/mhw.npy').astype(np.uint8)
tgt_idx=np.load('/tmp/w/tgt_idx.npy')
T=pd.DatetimeIndex(pd.read_csv('/tmp/w/T.csv',index_col=0,parse_dates=True).index)
lat=np.load('/tmp/w/lat.npy'); lon=np.load('/tmp/w/lon.npy')
times=T[tgt_idx]
os.makedirs('/tmp/w/out',exist_ok=True)
da=xr.DataArray(mhw,dims=('time','lat','lon'),coords={'time':times.values,'lat':lat,'lon':lon},name='mhw')
ds=xr.Dataset({'mhw':da})
ds.to_netcdf('/tmp/w/out/mhw_mask.nc')
ev=json.load(open('/tmp/w/events.json'))['events']
rep={'region':{'lat_min':57.33,'lat_max':58.53,'lon_min':9.03,'lon_max':10.23},
 'baseline_analysed':{'start':'1992-01-01','end':'2002-12-31'},
 'target_analysed':{'start':str(times[0].date()),'end':str(times[-1].date())},
 'events':ev,'complete':True,
 'caveats':'No regional MHW events found in 2012-06-01..2012-08-31. Land/sea: 3314 sea cells (finite all target days); 60x60 grid cells in region (lat 57.34-58.52, lon 9.04-10.22). Threshold/climatology pools use calendar dates from 1991-12-27 to 2003-01-05 as specified; baseline_analysed reports the nominal baseline years. Summer 2012 SST was near climatology (anomaly ~0) but stayed below the 90th-percentile threshold, with no run of 5 hot days in any cell (max run 3). Hot-day rate ~0.5% vs ~8.4% in baseline check.'}
os.makedirs('/tmp/w/out',exist_ok=True)
json.dump(rep,open('/tmp/w/out/report.json','w'),indent=2)
print(rep['events'], rep['target_analysed'], mhw.shape, mhw.sum())
'''
open('/tmp/w/wr.py','w').write(wr)
r=subprocess.run(['python','/tmp/w/wr.py'],capture_output=True,text=True); print(r.stdout, r.stderr[-2000:])
