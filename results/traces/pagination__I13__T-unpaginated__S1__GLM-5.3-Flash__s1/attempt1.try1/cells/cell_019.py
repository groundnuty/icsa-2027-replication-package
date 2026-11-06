import numpy as np, datetime as dt, json, os, warnings
import xarray as xr
warnings.filterwarnings('ignore')

cache = '/tmp/mhw_cache'
mhw = np.load(f'{cache}/mhw.npy')            # (92,60,60) uint8
with open(f'{cache}/dates.json') as f:
    dates = [dt.date.fromisoformat(s) for s in json.load(f)]
dates_t = dates[4028:]
lat_vals = np.load(f'{cache}/ref_lat.npy')   # float32 as stored in dataset
lon_vals = np.load(f'{cache}/ref_lon.npy')
sub_lat = lat_vals[130:190]
sub_lon = lon_vals[78:138]

os.makedirs('output', exist_ok=True)
print('cwd:', os.getcwd())

times = np.array([np.datetime64(d, 'ns') for d in dates_t])
ds_out = xr.Dataset(
    data_vars={
        'mhw': (('time', 'latitude', 'longitude'), mhw.astype('uint8'),
                {'long_name': 'marine heatwave mask (per-cell MHW)',
                 'flag_values': np.array([0, 1], dtype='uint8'),
                 'flag_meanings': 'not_in_mhw in_mhw',
                 'units': '1'}),
    },
    coords={
        'time': ('time', times, {'long_name': 'Time', 'standard_name': 'time', 'axis': 'T'}),
        'latitude': ('latitude', sub_lat.astype('float32'),
                     {'long_name': 'latitude', 'units': 'degrees_north', 'standard_name': 'latitude', 'axis': 'Y'}),
        'longitude': ('longitude', sub_lon.astype('float32'),
                      {'long_name': 'longitude', 'units': 'degrees_east', 'standard_name': 'longitude', 'axis': 'X'}),
    },
    attrs={
        'title': 'Marine heatwave (MHW) mask for a Baltic Sea region, June-August 2021',
        'product': 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m (Copernicus Marine Baltic Sea SST L4 reprocessed, daily)',
        'method': 'Per-cell 90th-percentile threshold (Hazen/Hyndman-Fan type 5) and mean climatology from 1992-2002 pooled +/-5 calendar days around each day of year, day 60 set to mean of days 59 and 61, both smoothed with a circular centred 31-day moving mean; hot day: SST >= threshold; per-cell MHW: run of >=5 hot days, gaps of 1-2 days joined; regional event: maximal run of days with at least one cell in MHW',
        'region_lat_min': 56.09, 'region_lat_max': 57.29,
        'region_lon_min': 10.55, 'region_lon_max': 11.75,
        'baseline_start': '1991-12-27', 'baseline_end': '2003-01-05',
        'target_start': '2021-06-01', 'target_end': '2021-08-31',
        'institution': 'research assistant (sandbox)',
        'Conventions': 'CF-1.8',
    },
)
enc = {'time': {'units': 'days since 1950-01-01 00:00:00', 'calendar': 'standard', 'dtype': 'int64'},
       'mhw': {'dtype': 'uint8', 'zlib': True, 'complevel': 4}}
ds_out.to_netcdf('output/mhw_mask.nc', engine='netcdf4', encoding=enc)
print('mhw_mask.nc written:', os.path.getsize('output/mhw_mask.nc'), 'bytes')

report = {
    "region": {"lat_min": 56.09, "lat_max": 57.29, "lon_min": 10.55, "lon_max": 11.75},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2021-06-01", "end": "2021-08-31"},
    "events": [{"onset": "2021-06-04", "end": "2021-07-28"}],
    "complete": True,
    "caveats": ("Sea cells are the 3296 region grid cells with finite SST on all 92 target days; other cells "
                "(mostly land, 304 of 3600) are 0. Coordinates are the dataset's native float32 grid values on "
                "the 0.02-degree grid; the cells nearest the inclusive requested bounds span 56.10-57.28 N and "
                "10.56-11.74 E, fully inside the region. Day 60 (29 Feb) has no pool of its own; its threshold "
                "and climatology were set to the mean of days 59 and 61 before smoothing, as specified. The "
                "baseline pools include the 5-day extensions beyond 1992-2002 (1991-12-27..1991-12-31 and "
                "2003-01-01..2003-01-05). Thresholds and climatology computed in float64; per-cell MHW runs "
                "restricted to and detected only within 2021-06-01..2021-08-31.")
}
with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print('report.json written:', os.path.getsize('output/report.json'), 'bytes')

# --- verify written files ---
ds_chk = xr.open_dataset('output/mhw_mask.nc', engine='netcdf4')
print()
print(ds_chk)
m = ds_chk['mhw'].values
print('mhw dtype:', ds_chk['mhw'].dtype, '| shape:', m.shape)
assert ds_chk['mhw'].dtype == np.uint8
assert m.shape == (92, 60, 60)
assert np.array_equal(m, mhw)
tv = ds_chk['time'].values
print('time first/last:', tv[0], tv[-1], '| n:', len(tv))
assert [str(t)[:10] for t in tv] == [d.isoformat() for d in dates_t]
lat_chk = ds_chk['latitude'].values; lon_chk = ds_chk['longitude'].values
assert np.array_equal(lat_chk.astype('float32'), sub_lat.astype('float32'))
assert np.array_equal(lon_chk.astype('float32'), sub_lon.astype('float32'))
print('lat range:', float(lat_chk[0]), '..', float(lat_chk[-1]))
print('lon range:', float(lon_chk[0]), '..', float(lon_chk[-1]))
print('mhw sum:', int(m.sum()))
ds_chk.close()

with open('output/report.json') as f:
    r = json.load(f)
print()
print(json.dumps(r, indent=2))
assert set(r.keys()) == {'region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats'}
print()
print('ALL OUTPUT FILES WRITTEN AND VERIFIED')