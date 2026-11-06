import xarray as xr, numpy as np, pickle, json, os

state = pickle.load(open('/work/state.pkl','rb'))
mhw, tgt_dates, sea, events = state['mhw'], state['tgt_dates'], state['sea'], state['events']
li, lo = state['li'], state['lo']

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
os.makedirs('output', exist_ok=True)

t0 = int(np.searchsorted(np.array(ds.indexes['time'].date), np.datetime64('2021-06-01')))
t1 = int(np.searchsorted(np.array(ds.indexes['time'].date), np.datetime64('2021-08-31')))
time_vals = ds['time'].isel(time=slice(t0, t1+1)).values
assert len(time_vals) == mhw.shape[0]
assert (time_vals.astype('datetime64[D]') == tgt_dates.astype('datetime64[D]')).all()

lat_vals = ds['latitude'].isel(lat=li).values
lon_vals = ds['longitude'].isel(lon=lo).values

out = xr.Dataset(
    {'mhw': xr.DataArray(mhw.astype(np.uint8), dims=('time','lat','lon'),
                         coords={'time': ('time', time_vals, ds['time'].attrs),
                                 'lat': ('lat', lat_vals, ds['latitude'].attrs),
                                 'lon': ('lon', lon_vals, ds['longitude'].attrs)},
                         attrs={'long_name': 'Marine heatwave mask (1 = inside a per-cell MHW, 0 otherwise)',
                                'description': 'Copernicus Baltic SST L4 reanalysis (cmems_obs-sst_bal_phy-temp_my_l4_P1D-m); '
                                               'per-cell MHW per published Baltic MHW method, target period 2021-06-01 to 2021-08-31.'})},
    attrs=ds.attrs)
out.to_netcdf('output/mhw_mask.nc')

report = {
    "region": {"lat_min": 54.45, "lat_max": 55.65, "lon_min": 16.05, "lon_max": 17.25},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2021-06-01", "end": "2021-08-31"},
    "events": [{"onset": e[0], "end": e[1]} for e in events],
    "complete": True,
    "caveats": ("308 of the 3600 region grid cells (Polish Pomeranian coast and adjacent coastal cells) are not sea cells "
                "(non-finite SST on at least one target day) and are set to 0; all 3292 sea cells had finite daily thresholds. "
                "Per the method, MHW detection is restricted to the target period, so the single regional event begins on the "
                "first target day (2021-06-01) and the underlying warm spell may have started earlier. The 90th percentile was "
                "computed with numpy method='hazen' (per the task specification, MATLAB quantile default), ignoring NaNs.")}
with open('output/report.json','w') as f:
    json.dump(report, f, indent=2)

chk = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(chk)
print('mhw dtype:', chk['mhw'].dtype, 'shape:', chk['mhw'].shape, 'sum:', int(chk['mhw'].sum()))
print('time:', chk['time'].values[0], '...', chk['time'].values[-1])
print('lat:', float(chk['lat'].values[0]), '...', float(chk['lat'].values[-1]))
print('lon:', float(chk['lon'].values[0]), '...', float(chk['lon'].values[-1]))
print(json.dumps(json.load(open('output/report.json')), indent=1))
print('sizes:', os.path.getsize('output/mhw_mask.nc'), os.path.getsize('output/report.json'))
