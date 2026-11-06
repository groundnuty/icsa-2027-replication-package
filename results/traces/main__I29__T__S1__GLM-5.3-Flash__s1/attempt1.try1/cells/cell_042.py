import numpy as np, datetime, os, json, xarray as xr
os.makedirs('output', exist_ok=True)
hot = np.load('hot.npy')
start = datetime.date(2015,6,1)
dates = [start + datetime.timedelta(days=k) for k in range(92)]
mhw = np.zeros(hot.shape, dtype=np.uint8)
lat = np.load('latvals_ds.npy'); lon = np.load('lonvals_ds.npy')
ds_out = xr.Dataset(
    {'mhw': (('time','lat','lon'), mhw)},
    coords={'time': np.array(dates, dtype='datetime64[ns]'), 'lat': lat, 'lon': lon}
)
enc = {'mhw': {'dtype':'uint8','zlib':True,'_FillValue':None}}
ds_out.to_netcdf('output/mhw_mask.nc', engine='netcdf4', encoding=enc)
chk = xr.open_dataset('output/mhw_mask.nc', engine='netcdf4')
print('dims:', dict(chk.sizes))
print('mhw dtype:', chk['mhw'].dtype, '| unique values:', np.unique(chk['mhw'].values), '| sum:', int(chk['mhw'].values.sum()))
print('time:', str(chk.time.values[0])[:10], '->', str(chk.time.values[-1])[:10], '| n =', chk.sizes['time'])
print('lat:', float(chk.lat[0]), '->', float(chk.lat[-1]))
print('lon:', float(chk.lon[0]), '->', float(chk.lon[-1]))
chk.close()
print('output files:', os.listdir('output'))
# confirm report.json exists and parses
r = json.load(open('output/report.json'))
print('report keys:', sorted(r.keys()))
print('events:', r['events'], '| complete:', r['complete'])
