code2 = r'''
import numpy as np, json, os, xarray as xr, pandas as pd
r=np.load('/work/res.npz')
mhw=r['mhw'].astype(np.uint8); tdates=r['tdates']; LAT=r['LAT']; LON=r['LON']
ev=json.load(open('/work/events.json'))['events']
os.makedirs('/work/output',exist_ok=True)
os.makedirs('output',exist_ok=True)
da=xr.DataArray(mhw,dims=('time','lat','lon'),coords={'time':pd.to_datetime(tdates),'lat':LAT,'lon':LON},name='mhw')
ds=xr.Dataset({'mhw':da})
ds['mhw'].attrs={'long_name':'marine heatwave per-cell flag'}
ds.to_netcdf('output/mhw_mask.nc', encoding={'mhw':{'dtype':'uint8','zlib':True}})
rep={'region':{'lat_min':59.05,'lat_max':60.25,'lon_min':21.25,'lon_max':22.45},
 'baseline_analysed':{'start':'1992-01-01','end':'2002-12-31'},
 'target_analysed':{'start':'2014-06-01','end':'2014-08-31'},
 'events':[{'onset':a,'end':b} for a,b in ev],
 'complete':True,
 'caveats':'Baseline uses 1992-2002 with +/-5-day windows reaching 1991-12-27..31 and 2003-01-01..05 (from the dataset files). Only the 60x60 grid cells within bounds were analysed (the dataset grid is 0.02 deg; the bounds fall between grid points so cells 59.06-60.24 N, 21.26-22.44 E are used). Sea cells are 3290 of 3600 (finite SST all target days); land cells set to 0. Files were read from the full-day NetCDFs; the dataset directory listing is capped at 1000 entries but all needed files exist and were downloaded directly. Events are truncated at 2014-08-31 by design.'}
json.dump(rep,open('output/report.json','w'),indent=2)
print(open('output/report.json').read())
'''
open('/work/write.py','w').write(code2)
import subprocess
r=subprocess.run(['python','/work/write.py'],capture_output=True,text=True,cwd='/work')
print(r.stdout[-3000:], r.stderr[-3000:])