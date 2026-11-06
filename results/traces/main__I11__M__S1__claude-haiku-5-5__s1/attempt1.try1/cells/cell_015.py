
import subprocess
code = r'''
import numpy as np, pandas as pd, json, os, xarray as xr
r=np.load('/tmp/w/res.npz')
mhw=r['mhw'].astype(np.uint8); T=pd.DatetimeIndex(r['T']); lat=r['lat'].astype(np.float32); lon=r['lon'].astype(np.float32)
os.makedirs('/work/output',exist_ok=True)
da=xr.DataArray(mhw,dims=('time','lat','lon'),coords={'time':T.values,'lat':lat,'lon':lon},name='mhw')
da.to_dataset().to_netcdf('/work/output/mhw_mask.nc')
active=mhw.any(axis=(1,2))
events=[]; i=0; n=len(active)
while i<n:
    if active[i]:
        j=i
        while j+1<n and active[j+1]: j+=1
        events.append({'onset':T[i].strftime('%Y-%m-%d'),'end':T[j].strftime('%Y-%m-%d')}); i=j+1
    else: i+=1
rep={'region':{'lat_min':55.67,'lat_max':56.87,'lon_min':16.45,'lon_max':17.65},
 'baseline_analysed':{'start':'1992-01-01','end':'2002-12-31'},
 'target_analysed':{'start':'2021-06-01','end':'2021-08-31'},
 'events':events,'complete':True,
 'caveats':'Region has 3600 grid cells (60x60 at 0.02 deg), of which 3310 are sea cells (finite on all target days); 290 land cells are 0 in mask. Per-cell MHWs are runs of >=5 hot days with 1-2 non-hot day gaps joined. Threshold and climatology use 1992-2002 with +/-5-day windows reaching into 1991-12-27..2003-01-05 as specified. Mask coordinates are dataset lat/lon values (float32).'}
json.dump(rep,open('/work/output/report.json','w'),indent=2)
print(json.dumps(rep,indent=1)[:1500])
print(xr.open_dataset('/work/output/mhw_mask.nc').mhw.shape)
'''
open('/tmp/w/s3.py','w').write(code)
r=subprocess.run(['python','/tmp/w/s3.py'],capture_output=True,text=True); print(r.stdout, r.stderr[-3000:])
print(subprocess.run('ls -la /work/output',shell=True,capture_output=True,text=True).stdout)