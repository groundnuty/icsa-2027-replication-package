import numpy as np, json, datetime as dt, os
import xarray as xr

os.makedirs('/work/output', exist_ok=True)
mask = np.load('/tmp/mhw_mask.npy').astype(np.uint8)     # (92, 60, 60)
sea = np.load('/tmp/sea.npy')
meta = json.load(open('/tmp/meta.json'))
i0,i1,j0,j1 = meta['idx']
tgt = [dt.date.fromisoformat(s) for s in meta['tgt']]
ev = json.load(open('/tmp/ev.json'))['events']

# coordinate values: read region slices from a target file with xarray
import fsspec, h5py
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
with fs.open(f'{base}/sst_20220601.nc','rb') as f:
    with h5py.File(f,'r') as h:
        lat = h['latitude'][i0:i1+1].astype(np.float64)
        lon = h['longitude'][j0:j1+1].astype(np.float64)

times = np.array([np.datetime64(d, 'ns') for d in tgt])
ds = xr.Dataset(
    {'mhw': (('time','lat','lon'), mask)},
    coords={'time': times, 'lat': lat, 'lon': lon},
)
ds['mhw'].attrs = {'long_name': 'marine heatwave (per-cell MHW) mask', 'flag_values': np.array([0,1], dtype=np.uint8), 'flag_meanings': 'not_in_mhw in_mhw'}
ds['lat'].attrs = {'standard_name':'latitude','units':'degrees_north'}
ds['lon'].attrs = {'standard_name':'longitude','units':'degrees_east'}
enc = {'mhw': {'dtype':'uint8', 'zlib': True, 'complevel': 4}, 'time': {'units':'days since 1900-01-01','calendar':'proleptic_gregorian','dtype':'int32'}}
ds.to_netcdf('/work/output/mhw_mask.nc', engine='h5netcdf', encoding=enc)

report = {
    'region': {'lat_min': 54.81, 'lat_max': 56.01, 'lon_min': 19.61, 'lon_max': 20.81},
    'baseline_analysed': {'start': '1992-01-01', 'end': '2002-12-31'},
    'target_analysed': {'start': '2022-06-01', 'end': '2022-08-31'},
    'events': [{'onset': e['onset'], 'end': e['end']} for e in ev],
    'complete': True,
    'caveats': '',
}
with open('/work/output/report.json','w') as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2))

# verify written files
ds2 = xr.open_dataset('/work/output/mhw_mask.nc')
print('\n--- verify mhw_mask.nc ---')
print(ds2)
print('mhw dtype:', ds2.mhw.dtype, '| shape:', ds2.mhw.shape)
m2 = ds2.mhw.values
print('uint8:', m2.dtype==np.uint8, '| identical to computed mask:', np.array_equal(m2, mask))
print('time[0], time[-1]:', ds2.time.values[0], ds2.time.values[-1])
print('lat[0], lat[-1]:', ds2.lat.values[0], ds2.lat.values[-1], '| lon[0], lon[-1]:', ds2.lon.values[0], ds2.lon.values[-1])
r2 = json.load(open('/work/output/report.json'))
print('\nreport fields:', sorted(r2.keys()))
assert set(r2.keys()) == {'region','baseline_analysed','target_analysed','events','complete','caveats'}
print('files:', os.listdir('/work/output'), '| sizes:', {f: os.path.getsize(f'/work/output/{f}') for f in os.listdir('/work/output')})
