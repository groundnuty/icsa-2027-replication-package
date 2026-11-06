
import numpy as np, json, os, xarray as xr, datetime as dt
r=np.load('/tmp/res.npz')
mhw=r['mhw'].astype(np.uint8); tdates=[dt.datetime.strptime(s,'%Y%m%d') for s in r['tdates']]
lat=r['lat']; lon=r['lon']; events=r['events']
os.makedirs('output',exist_ok=True)
da=xr.Dataset({'mhw':(('time','lat','lon'),mhw)},
    coords={'time':('time',np.array(tdates,dtype='datetime64[ns]')),'lat':('lat',lat),'lon':('lon',lon)})
da.to_netcdf('output/mhw_mask.nc',engine='h5netcdf')
rep={"region":{"lat_min":58.69,"lat_max":59.89,"lon_min":18.69,"lon_max":19.89},
 "baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},
 "target_analysed":{"start":"2010-06-01","end":"2010-08-31"},
 "events":[{"onset":str(a),"end":str(b)} for a,b in events],
 "complete":True,
 "caveats":"Per-cell MHW mask set to 0 for the 307 region cells that are not sea cells (NaN on some target day); their hot days were not evaluated. Baseline pools use the ±5-day windows including the 1991-12-27..1991-12-31 and 2003-01-01..2003-01-05 extensions. Dataset listing via fsspec was capped at 1000 files, so files were read by constructed path (all found)."}
json.dump(rep,open('output/report.json','w'),indent=2)
print(open('output/report.json').read())
print(xr.open_dataset('output/mhw_mask.nc',engine='h5netcdf'))
