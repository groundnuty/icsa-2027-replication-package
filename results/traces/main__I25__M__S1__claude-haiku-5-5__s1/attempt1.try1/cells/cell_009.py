write=r'''
import numpy as np, xarray as xr, json, os, datetime as dt
mhw=np.load('/tmp/out/mhw.npy'); ev=json.load(open('/tmp/out/ev.json'))['events']
z=np.load('/tmp/sub.npz'); latv=z['lat']; lonv=z['lon']; dates=[dt.date.fromisoformat(s) for s in z['dates']]
tgt=[x for x in dates if dt.date(2016,6,1)<=x<=dt.date(2016,8,31)]
os.makedirs('/data_out_placeholder',exist_ok=True) if False else None
os.makedirs('output',exist_ok=True)
da=xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype(np.uint8))},
  coords={'time':('time',np.array([np.datetime64(x.isoformat()) for x in tgt],dtype='datetime64[ns]')),
          'lat':('lat',latv.astype(np.float32)),'lon':('lon',lonv.astype(np.float32))})
da.to_netcdf('output/mhw_mask.nc',encoding={'mhw':{'dtype':'uint8','zlib':True}})
rep={'region':{'lat_min':57.57,'lat_max':58.77,'lon_min':10.25,'lon_max':11.45},
 'baseline_analysed':{'start':'1992-01-01','end':'2002-12-31'},
 'target_analysed':{'start':'2016-06-01','end':'2016-08-31'},
 'events':[{'onset':a,'end':b} for a,b in ev],
 'complete':True,
 'caveats':'Threshold/climatology pooled from 1992-2002 with +-5 day windows (extending to 1991-12-27 and 2003-01-05). Hazen quantile per cell and doy; 31-day circular smoothing. Per-cell MHWs require >=5 hot days; gaps of 1-2 non-hot days joined. Regional events are maximal runs of days with any cell in an MHW; events truncated at the target-period boundaries (event 2016-06-01 may have started before the analysed period). Land cells (296 of 3600) are 0.'}
json.dump(rep,open('output/report.json','w'),indent=2)
print(open('output/report.json').read())
'''
open('/tmp/write.py','w').write(write)
r=subprocess.run(['python','/tmp/write.py'],capture_output=True,text=True,cwd='/tmp'); print(r.stdout, r.stderr[-2000:])
print(subprocess.run('ls -la /tmp/output; ',shell=True,capture_output=True,text=True).stdout)