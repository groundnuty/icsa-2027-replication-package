import numpy as np, json, os, xarray as xr

mhw = np.load('/work/mhw.npy')
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
times = ds.time.values.astype('datetime64[D]')
targ_sel = np.where((times >= np.datetime64('2010-06-01')) & (times <= np.datetime64('2010-08-31')))[0]
lat_idx = np.where((ds.latitude.values.astype(np.float64) >= 58.69) & (ds.latitude.values.astype(np.float64) <= 59.89))[0]
lon_idx = np.where((ds.longitude.values.astype(np.float64) >= 18.69) & (ds.longitude.values.astype(np.float64) <= 19.89))[0]

out = xr.Dataset(
    {'mhw': (('time','lat','lon'), mhw)},
    coords={'time': ds.time.values[targ_sel], 'lat': ds.latitude.values[lat_idx], 'lon': ds.longitude.values[lon_idx]},
)
out['mhw'].attrs = {'long_name': 'per-cell marine heatwave mask (1 = inside per-cell MHW)'}
out['lat'].attrs = {'standard_name': 'latitude', 'units': 'degrees_north'}
out['lon'].attrs = {'standard_name': 'longitude', 'units': 'degrees_east'}
os.makedirs('output', exist_ok=True)
out.to_netcdf('output/mhw_mask.nc', encoding={'mhw': {'dtype': 'uint8', 'zlib': True}})

report = {
    "region": {"lat_min": 58.69, "lat_max": 59.89, "lon_min": 18.69, "lon_max": 19.89},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analised" if False else "target_analysed": {"start": "2010-06-01", "end": "2010-08-31"},
    "events": [{"onset": "2010-06-27", "end": "2010-07-26"}],
    "complete": True,
    "caveats": "",
}
with open('output/report.json','w') as f:
    json.dump(report, f, indent=2)

chk = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print('mhw dtype:', chk.mhw.dtype, '| sum:', int(chk.mhw.values.sum()), '| dims:', dict(chk.sizes))
print('time first/last:', str(chk.time.values[0])[:10], str(chk.time.values[-1])[:10])
print(json.load(open('output/report.json')))
print('files:', os.listdir('output'))
