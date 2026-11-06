
import subprocess
writer = r'''
import numpy as np, json, os, xarray as xr
g=np.load('/tmp/sub/grid.npz'); lat=g['lat']; lon=g['lon']
il=np.where((lat>=57.41)&(lat<=58.61))[0]; jl=np.where((lon>=18.69)&(lon<=19.89))[0]
r=np.load('/tmp/out/res.npz'); j=json.load(open('/tmp/out/res.json'))
mhw=r['mhw'].astype(np.uint8)
times=np.array(j['tgt'],dtype='datetime64[ns]')
ds=xr.Dataset({'mhw':(('time','lat','lon'),mhw)},
   coords={'time':times,'lat':lat[il],'lon':lon[jl]})
os.makedirs('/code/output',exist_ok=True) if False else None
os.makedirs('output',exist_ok=True)
ds.to_netcdf('output/mhw_mask.nc', encoding={'mhw':{'dtype':'uint8','zlib':True}})
rep={'region':{'lat_min':57.41,'lat_max':58.61,'lon_min':18.69,'lon_max':19.89},
     'baseline_analysed':{'start':'1992-01-01','end':'2002-12-31'},
     'target_analysed':{'start':'2004-06-01','end':'2004-08-31'},
     'events':j['events'],
     'complete':True,
     'caveats':('No per-cell MHW (run of >=5 hot days) occurred in any of the 3309 sea cells in the target period; '
                'the longest hot run was 4 days, so the regional event list is empty. Baseline pools use the calendar windows '
                'for 1992-2002 (extension days 1991-12-27..31 and 2003-01-01..05 included). Threshold/climatology NaN-free for sea cells. '
                'Land cells are 0 in the mask. Day of year follows the leap-year calendar mapping (day 60 skipped in non-leap years).')}
json.dump(rep,open('output/report.json','w'),indent=2)
print(ds)
print(open('output/report.json').read())
'''
open('/tmp/write.py','w').write(writer)
r=subprocess.run(['python','/tmp/write.py'],capture_output=True,text=True,cwd='/tmp')
print(r.stdout[-4000:], r.stderr[-3000:])
