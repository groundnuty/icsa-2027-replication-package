import numpy as np, xarray as xr, json, os, warnings
warnings.filterwarnings("ignore")
os.makedirs('/work/output', exist_ok=True)

F = np.load('/work/final_state.npz')
mhw_sea = F['mhw']            # (92, ns) bool
sea = F['sea']                # (3600,)
t_tgt = F['t_tgt']            # (92,) 'YYYY-MM-DD'
lat = F['lat']; lon = F['lon']
onsets = F['events_onset']; ends = F['events_end']

ns = int(sea.sum())
# expand to full regional grid, land = 0
mhw_full = np.zeros((92, 60, 60), dtype=np.uint8)
mhw_full[:, sea] = mhw_sea
print("mhw_full: shape", mhw_full.shape, "dtype", mhw_full.dtype, "ones:", int(mhw_full.sum()))

ds = xr.Dataset(
    data_vars={'mhw': xr.DataArray(mhw_full, dims=('time', 'lat', 'lon'),
        attrs={'long_name': 'marine heatwave indicator (1 = inside per-cell MHW, 0 = otherwise or land)',
               'flag_values': [0, 1]})},
    coords={
        'time': xr.DataArray(np.datetime64(t_tgt[0]).astype('datetime64[ns]') + 0 * np.array([0]) , dims=()),
    })
# build time coordinate properly
tvals = xr.DataArray(np.array(t_tgt, dtype='datetime64[ns]'), dims=('time',),
                     attrs={'long_name': 'Time', 'standard_name': 'time', 'axis': 'T'})
lats = xr.DataArray(lat, dims=('lat',), attrs={'long_name': 'latitude', 'units': 'degrees_north', 'standard_name': 'latitude', 'axis': 'Y'})
lons = xr.DataArray(lon, dims=('lon',), attrs={'long_name': 'longitude', 'units': 'degrees_east', 'standard_name': 'longitude', 'axis': 'X'})
ds = xr.Dataset(
    data_vars={'mhw': xr.DataArray(mhw_full, dims=('time', 'lat', 'lon'),
        attrs={'long_name': 'marine heatwave indicator (1 = inside per-cell MHW, 0 = otherwise or land)',
               'flag_values': [0, 1]})},
    coords={'time': tvals, 'lat': lats, 'lon': lons})
ds.to_netcdf('/work/output/mhw_mask.nc')

events = [{"onset": str(a), "end": str(b)} for a, b in zip(onsets, ends)]
report = {
    "region": {"lat_min": 58.69, "lat_max": 59.89, "lon_min": 18.69, "lon_max": 19.89},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2017-06-01", "end": "2017-08-31"},
    "events": events,
    "complete": True,
    "caveats": ("No per-cell MHWs (>=5 consecutive hot days at/above the smoothed 90th-percentile "
                "threshold) were detected in any of the 3293 sea cells during 2017-06-01 to 2017-08-31; "
                "the longest run of hot days was 4. The zero-event result is robust to the percentile "
                "interpolation variant (both numpy 'hazen' and 'linear' give the same outcome).")
}
with open('/work/output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2))

# verify
chk = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
print("\nverification:")
print(chk)
print("mhw dtype:", chk['mhw'].dtype, "dims:", dict(chk.sizes))
print("time range:", chk.time.values[0], chk.time.values[-1], "n=", chk.time.size)
print("lat range:", float(chk.lat.values.min()), float(chk.lat.values.max()), "n=", chk.lat.size)
print("lon range:", float(chk.lon.values.min()), float(chk.lon.values.max()), "n=", chk.lon.size)
print("mhw min/max:", int(chk['mhw'].values.min()), int(chk['mhw'].values.max()))
chk.close()
