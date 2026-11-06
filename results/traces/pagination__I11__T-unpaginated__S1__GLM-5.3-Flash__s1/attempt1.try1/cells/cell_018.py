import numpy as np, json, os, datetime as dt
import xarray as xr

mhw = np.load('cache/mhw.npy')
tgt = np.load('cache/tgt.npy')
meta = json.load(open('cache/meta.json'))
dates_tgt = [dt.date.fromisoformat(s) for s in meta['dates_tgt']]
lat_full = np.array(meta['lat']); lon_full = np.array(meta['lon'])
lat = lat_full[109:169]; lon = lon_full[373:433]
print('lat sub:', lat[0], '..', lat[-1], '| lon sub:', lon[0], '..', lon[-1])
sea = np.isfinite(tgt).all(axis=0)
assert not mhw[:, ~sea].any()
mhw_u8 = mhw.astype(np.uint8)

os.makedirs('output', exist_ok=True)
time_coord = np.array([np.datetime64(d.isoformat(), 'ns') for d in dates_tgt])
da = xr.DataArray(
    mhw_u8, dims=('time', 'lat', 'lon'),
    coords={'time': time_coord, 'lat': ('lat', lat), 'lon': ('lon', lon)},
    name='mhw',
    attrs={'long_name': 'marine heatwave (per-cell) mask',
           'flag_values': np.array([0, 1], dtype=np.uint8),
           'flag_meanings': 'not_in_mhw in_mhw',
           'units': '1'})
ds = xr.Dataset({'mhw': da})
ds['lat'].attrs = {'long_name': 'latitude', 'units': 'degrees_north', 'standard_name': 'latitude'}
ds['lon'].attrs = {'long_name': 'longitude', 'units': 'degrees_east', 'standard_name': 'longitude'}
ds['time'].attrs = {'long_name': 'Time', 'standard_name': 'time', 'axis': 'T'}
ds.attrs = {'title': 'Per-cell marine heatwave mask, Baltic Sea region 55.67-56.87N 16.45-17.65E, 2021-06-01..2021-08-31',
            'source_dataset': 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m (SST_BAL_SST_L4_REP_OBSERVATIONS_010_016, DMI, version 202506)',
            'baseline': '1992-01-01..2002-12-31 (pools extend +/-5 days: 1991-12-27..1991-12-31, 2003-01-01..2003-01-05)',
            'method': 'threshold = 90th percentile (hazen/type 5) of +/-5-calendar-day day-of-year pools, day 60 = mean(days 59,61), '
                      'smoothed with centred 31-day circular moving mean; hot: SST >= threshold; per-cell MHW: >=5 consecutive hot days, gaps <=2 days joined'}
ds.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print('wrote output/mhw_mask.nc')

report = {
    'region': {'lat_min': 55.67, 'lat_max': 56.87, 'lon_min': 16.45, 'lon_max': 17.65},
    'baseline_analysed': {'start': '1992-01-01', 'end': '2002-12-31'},
    'target_analysed': {'start': '2021-06-01', 'end': '2021-08-31'},
    'events': [{'onset': '2021-06-05', 'end': '2021-08-01'}],
    'complete': True,
    'caveats': ('Grid cells were selected from the 0.02-degree dataset grid by inclusive coordinate bounds; '
                'the selected 60x60 cells span 55.68-56.86 N and 16.46-17.64 E (no grid point lies exactly on the bounds). '
                '3310 of 3600 cells are sea cells (finite SST on every target day); the remaining 290 are land (mask 0). '
                'Baseline pools additionally include the days 1991-12-27..1991-12-31 and 2003-01-01..2003-01-05, as required by the +/-5-day windows at the baseline edges. '
                'No target or pool day had missing SST for any sea cell (dataset complete over the needed ranges).')}
with open('output/report.json', 'w') as fh:
    json.dump(report, fh, indent=2)
print('wrote output/report.json')

chk = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(chk)
v = chk['mhw']
print('dtype:', v.dtype, '| dims:', v.dims, '| shape:', v.shape, '| sum:', int(v.values.sum()))
print('time:', chk['time'].values[0], '->', chk['time'].values[-1], '| n:', chk['time'].size)
print('lat:', float(chk['lat'][0]), '..', float(chk['lat'][-1]), '| lon:', float(chk['lon'][0]), '..', float(chk['lon'][-1]))
assert v.dtype == np.uint8 and v.dims == ('time', 'lat', 'lon')
assert np.array_equal(v.values, mhw_u8)
assert int(v.values.sum()) == int(mhw.sum())
chk.close()
rep = json.load(open('output/report.json'))
print('report keys:', sorted(rep.keys()))
print('events:', rep['events'], '| complete:', rep['complete'])
