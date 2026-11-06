import os, json
os.makedirs('/work/output', exist_ok=True)
events = json.load(open('/work/events.json'))['events']
print('events:', events)

import numpy as np
mhw = np.load('/work/mhw.npy')
print('mhw sum (should be 0):', int(mhw.sum()), 'shape', mhw.shape)

import xarray as xr
ds0 = xr.open_dataset('/work/nc/sst_20170715.nc', engine='h5netcdf')
lat = ds0['latitude'].isel(latitude=slice(438,498)).values
lon = ds0['longitude'].isel(longitude=slice(487,547)).values
time = np.array([np.datetime64(f'{d}T00:00:00', 'ns') for d in [s for s in json.load(open('/work/dates.json'))['target']]])

da = xr.DataArray(
    data=mhw.astype(np.uint8),
    coords={'time': time, 'lat': ('lat', lat), 'lon': ('lon', lon)},
    dims=('time','lat','lon'),
    name='mhw',
    attrs={'long_name': 'marine heatwave (per-cell) mask', 'flag_values': np.array([0,1],dtype='uint8'),
           'flag_meanings': 'not_in_mhw in_mhw', 'units': '1'}
)
out = xr.Dataset({'mhw': da})
out['time'].attrs = {'long_name':'Time','standard_name':'time','axis':'T'}
out['lat'].attrs = {'units':'degrees_north','standard_name':'latitude','axis':'Y'}
out['lon'].attrs = {'units':'degrees_east','standard_name':'latitude','axis':'X'}
out.attrs = {
    'title': 'Per-cell marine heatwave mask, Baltic Sea region, Jun-Aug 2017',
    'method': 'baseline 1992-2002 climatology and 90th percentile (Hazen), circular 31-day smoothing; runs >=5 days, gaps <=2 joined',
    'source_dataset': 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m',
}
out.to_netcdf('/work/output/mhw_mask.nc', engine='h5netcdf')

report = {
  "region": {"lat_min": 62.25, "lat_max": 63.45, "lon_min": 18.73, "lon_max": 19.93},
  "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
  "target_analysed": {"start": "2017-06-01", "end": "2017-08-31"},
  "events": events,
  "complete": True,
  "caveats": ""
}
with open('/work/output/report.json','w') as f:
    json.dump(report, f, indent=2)
print('written')

# verify outputs
v = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
print(v)
print('mhw dtype', v['mhw'].dtype, 'sum', int(v['mhw'].values.sum()))
print(json.dumps(json.load(open('/work/output/report.json')), indent=1))
