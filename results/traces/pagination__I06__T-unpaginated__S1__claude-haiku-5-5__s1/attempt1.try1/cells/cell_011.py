out = r'''
import numpy as np, datetime as dt, json, xarray, pandas as pd
r=np.load('work/res.npz')
mhw=r['mhw'].astype(np.uint8); td=[dt.date.fromisoformat(s) for s in r['tdates']]
lat=r['lat']; lon=r['lon']; sea=r['sea']
# land cells zero (already by construction)
mhw=mhw*sea[None].astype(np.uint8)
times=pd.to_datetime([str(d) for d in td])
ds=xarray.Dataset({'mhw':(('time','lat','lon'),mhw)},
    coords={'time':times,'lat':lat,'lon':lon})
ds['mhw'].attrs={'long_name':'marine heatwave flag per cell'}
ds['mhw'].encoding={'dtype':'uint8'}
ds.to_netcdf('output/mhw_mask.nc')
exec(open('work/mhw.py').read().split("tgt=[i")[0]) if False else None
# events from mask (regional union)
active=mhw.any(axis=(1,2))
events=[];i=0
while i<len(active):
    if active[i]:
        j=i
        while j+1<len(active) and active[j+1]: j+=1
        events.append({'onset':str(td[i]),'end':str(td[j])}); i=j+1
    else: i+=1
rep={'region':{'lat_min':54.45,'lat_max':55.65,'lon_min':16.05,'lon_max':17.25},
 'baseline_analysed':{'start':'1992-01-01','end':'2002-12-31'},
 'target_analysed':{'start':'2012-06-01','end':'2012-08-31'},
 'events':events,'complete':True,
 'caveats':('Baseline window pool uses dates 1991-12-27..2003-01-05 (edge windows). Day-of-year via leap-year table (Feb29=60). '
  'Sea cells = finite on all target days (3292 of 3600). Land cells written as 0. Threshold/climatology computed in float64 from float32 stored kelvin. '
  'Per-cell MHWs = maximal hot runs >=5 days, merged when separated by 1-2 non-hot days. Event end = last active day. Mask grid is the 60x60 region subset of the dataset grid (lat 54.46-55.64, lon 16.06-17.24).')}
json.dump(rep,open('output/report.json','w'),indent=2)
print(json.dumps(rep,indent=2)[:1500])
'''
open('work/out.py','w').write(out)
exec(compile(out,'out','exec'))
import xarray as xr
print(xr.open_dataset('output/mhw_mask.nc')['mhw'].shape, xr.open_dataset('output/mhw_mask.nc')['mhw'].dtype)