import numpy as np, os, json, xarray as xr

lat_reg = np.load('/tmp/lat_reg.npy')  # (60,) float64, exact dataset float32 values
lon_reg = np.load('/tmp/lon_reg.npy')
dates = np.load('/tmp/dates.npy')
tgt_dates = dates[14031:14123]
mhw_full = np.load('/tmp/mhw_full.npy')

ds = xr.Dataset(
    {'mhw': (('time', 'lat', 'lon'), mhw_full)},
    coords={'time': tgt_dates.astype('datetime64[ns]'), 'lat': lat_reg, 'lon': lon_reg},
)
enc = {'mhw': {'zlib': True, 'complevel': 4, '_FillValue': None, 'dtype': 'uint8'},
       'time': {'units': 'seconds since 1981-01-01', 'calendar': 'proleptic_gregorian'},
       'lat': {'dtype': 'float32'}, 'lon': {'dtype': 'float32'}}
ncpath = '/work/output/mhw_mask.nc'
ds.to_netcdf(ncpath, engine='h5netcdf', encoding=enc)
print('rewrote', ncpath, os.path.getsize(ncpath)/1e6, 'MB')

# final verification, including bitwise coords vs dataset
fss = __import__('fsspec').filesystem('onedata')
import h5py
hf = h5py.File(fss.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','rb'), 'r')
lat_ds = hf['latitude'][45:105]; lon_ds = hf['longitude'][463:523]
hf.close()
hw = h5py.File(ncpath, 'r')
lat_w = hw['lat'][:]; lon_w = hw['lon'][:]
m = hw['mhw']
print('lat bitwise equal to dataset:', np.array_equal(lat_w.view(np.uint32), lat_ds.view(np.uint32)))
print('lon bitwise equal to dataset:', np.array_equal(lon_w.view(np.uint32), lon_ds.view(np.uint32)))
print('mhw:', m.shape, m.dtype, 'fillvalue attr:', '_FillValue' in m.attrs, 'sum:', int(m[:].sum()))
tv = hw['time'][:]
print('time first/last:', np.datetime64('1981-01-01') + tv[0]*1000000000, np.datetime64('1981-01-01') + tv[-1]*1000000000, 'n=', len(tv))
hw.close()
ds2 = xr.open_dataset(ncpath, engine='h5netcdf'); print(ds2.mhw.dtype, dict(ds2.sizes)); ds2.close()

rep = json.load(open('/work/output/report.json'))
print('report ok:', sorted(rep.keys()), '| events:', rep['events'], '| complete:', rep['complete'])
