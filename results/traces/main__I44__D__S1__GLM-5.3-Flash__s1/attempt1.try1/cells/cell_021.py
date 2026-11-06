import numpy as np, datetime as dt, json
from netCDF4 import Dataset, num2date

p='/work/output/mhw_mask.nc'
nc=Dataset(p,'r')
print('dims:', {k:len(v) for k,v in nc.dimensions.items()})
print('vars:', list(nc.variables))
v=nc.variables['mhw']
print('mhw dtype:', v.dtype, 'shape:', v.shape, 'chunking:', v.chunking())
m=v[:]
print('mask sum:', int(np.sum(m)), 'unique:', np.unique(m))
lat=nc.variables['lat'][:]; lon=nc.variables['lon'][:]
t=nc.variables['time']
print('lat range:', float(lat.min()), float(lat.max()), 'n', lat.size)
print('lon range:', float(lon.min()), float(lon.max()), 'n', lon.size)
print('time units:', t.units, '| first/last:', num2date(t[0], t.units, t.calendar), num2date(t[-1], t.units, t.calendar))
tdates=[num2date(x, t.units, t.calendar).strftime('%Y-%m-%d') for x in t[:]]
print('first/last date strings:', tdates[0], tdates[-1], 'n days:', len(tdates))
# re-derive regional events from file
mm=np.asarray(v[:].data).astype(bool)
idx=np.flatnonzero(mm.any(axis=(1,2)))
br=np.flatnonzero(np.diff(idx)>1)
st=np.r_[idx[0], idx[br+1]]; en=np.r_[idx[br], idx[-1]]
ev=[{'onset':tdates[a], 'end':tdates[b]} for a,b in zip(st,en)]
print('events from file:', ev)
nc.close()

rep=json.load(open('/work/output/report.json'))
print('\nreport keys:', sorted(rep.keys()))
print(json.dumps({k:rep[k] for k in ['region','baseline_analysed','target_analysed','events','complete']}, indent=1))
print('events match file-derived:', rep['events']==ev)
assert set(rep.keys())=={'region','baseline_analysed','target_analysed','events','complete','caveats'}
assert rep['events']==ev and rep['complete'] is True
print('\nALL CHECKS PASSED')
