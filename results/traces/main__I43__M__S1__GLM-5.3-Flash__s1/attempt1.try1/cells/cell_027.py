import numpy as np, json, os
from datetime import date
import netCDF4

os.makedirs('/work/output', exist_ok=True)
z = np.load('/work/cubes.npz')
targ_ds = [date.fromisoformat(str(s)) for s in z['targ_dates']]
import h5py
with h5py.File('/data/icsa2027_data_20261101T090944Z/s1z/sst_20170601.nc','r') as f:
    lat = f['latitude'][438:498].astype('float64')
    lon = f['longitude'][487:547].astype('float64')
ILAT, ILON = slice(438,498), slice(487,547)

# mhw mask: (92, 60, 60) uint8, 0 everywhere (no hot days)
mhw = np.zeros((len(targ_ds), 60, 60), dtype='uint8')

p = '/work/output/mhw_mask.nc'
ds = netCDF4.Dataset(p, 'w', format='NETCDF4')
ds.createDimension('time', len(targ_ds))
ds.createDimension('lat', 60)
ds.createDimension('lon', 60)
tv = ds.createVariable('time', 'f8', ('time',))
tv.units = 'seconds since 1981-01-01'; tv.calendar = 'proleptic_gregorian'; tv.standard_name='time'; tv.axis='T'
tv[:] = np.array([(d - date(1981,1,1)).total_seconds() for d in targ_ds])
lv = ds.createVariable('lat', 'f8', ('lat',)); lv.units='degrees_north'; lv.standard_name='latitude'; lv.axis='Y'
lv[:] = lat
lov = ds.createVariable('lon', 'f8', ('lon',)); lov.units='degrees_east'; lov.standard_name='longitude'; lov.axis='X'
lov[:] = lon
mv = ds.createVariable('mhw', 'u1', ('time','lat','lon')); mv.long_name='marine heatwave per-cell mask'
mv.coordinates = 'time lat lon'
mv[:] = mhw
ds.setncattr('title', 'Baltic Sea marine heatwave mask, 2017-06-01..2017-08-31, region 62.25-63.45N 18.73-19.93E')
ds.setncattr('source_dataset', 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m')
ds.close()
print('wrote', p, os.path.getsize(p), 'bytes')

report = {
  "region": {"lat_min": 62.25, "lat_max": 63.45, "lon_min": 18.73, "lon_max": 19.93},
  "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
  "target_analysed": {"start": "2017-06-01", "end": "2017-08-31"},
  "events": [],
  "complete": True,
  "caveats": ""
}
with open('/work/output/report.json','w') as f:
    json.dump(report, f, indent=2)
print('wrote /work/output/report.json')
print(json.dumps(report))

# ---- verify outputs ----
d = netCDF4.Dataset(p)
print('vars:', {k: (d[k].dtype, d[k].shape) for k in d.variables})
print('time[:3]:', d['time'][:3], '... time[-1]:', d['time'][-1])
print('mhw dtype/shape:', d['mhw'].dtype, d['mhw'].shape, 'unique:', np.unique(d['mhw'][:]))
print('lat range: %.6f..%.6f  lon range: %.6f..%.6f' % (d['lat'][:].min(), d['lat'][:].max(), d['lon'][:].min(), d['lon'][:].max()))
d.close()
# time values match target dates?
tt = [date(1981,1,1)+__import__('datetime').timedelta(seconds=s) for s in netCDF4.Dataset(p)['time'][:]]
print('time decode == target dates:', tt == targ_ds)
with open('/work/output/report.json') as f:
    r = json.load(f)
print('report keys:', sorted(r.keys()))
