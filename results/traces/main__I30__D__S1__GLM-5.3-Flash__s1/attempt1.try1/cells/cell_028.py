import numpy as np, json, datetime as dt, xarray as xr

mhw = np.load('/work/mhw.npy')
sea = np.load('/work/sea.npy')

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat = ds.latitude.values.astype(np.float64)
lon = ds.longitude.values.astype(np.float64)
lat_idx = np.where((lat >= 58.69) & (lat <= 59.89))[0]
lon_idx = np.where((lon >= 18.69) & (lon <= 19.89))[0]
times = ds.time.values.astype('datetime64[D]')
targ_sel = np.where((times >= np.datetime64('2010-06-01')) & (times <= np.datetime64('2010-08-31')))[0]
t_coord = ds.time.values[targ_sel]
lat_c = ds.latitude.values[lat_idx]
lon_c = ds.longitude.values[lon_idx]
assert mhw.shape == (len(t_coord), len(lat_c), len(lon_c))

out = xr.Dataset(
    {'mhw': (('time','lat','lon'), mhw)},
    coords={'time': t_coord, 'lat': lat_c, 'lon': lon_c},
)
out['mhw'].attrs = {'long_name': 'per-cell marine heatwave mask (1 = inside per-cell MHW)'}
out['lat'].attrs = {'standard_name': 'latitude', 'units': 'degrees_north'}
out['lon'].attrs = {'standard_name': 'longitude', 'units': 'degrees_east'}
enc = {'mhw': {'dtype': 'uint8', 'zlib': True}}
os.makedirs('output', exist_ok=True)
out.to_netcdf('output/mhw_mask.nc', encoding=enc)
print('wrote output/mhw_mask.nc')

report = {
    "region": {"lat_min": 58.69, "lat_max": 59.89, "lon_min": 18.69, "lon_max": 19.89},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2010-06-01", "end": "2010-08-31"},
    "events": [{"onset": "2010-06-27", "end": "2010-07-26"}],
    "complete": True,
    "caveats": "",
}
with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print('wrote output/report.json')

# verify outputs read back correctly
chk = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(chk)
print('mhw dtype:', chk.mhw.dtype, 'sum:', int(chk.mhw.values.sum()))
print(json.load(open('output/report.json')))
