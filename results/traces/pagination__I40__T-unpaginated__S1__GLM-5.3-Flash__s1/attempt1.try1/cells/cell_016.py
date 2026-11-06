import numpy as np, json, os, datetime as dt
import xarray as xr

A = np.load('analysis.npz')
mhw = A['mhw']; sea = A['sea']; thr = A['thr']; clim = A['clim']
tgt_dates = np.load('tgt_dates.npy')
lat_full = np.load('lat.npy'); lon_full = np.load('lon.npy')
i0,i1,j0,j1 = 404,463,559,618
lat = lat_full[i0:i1+1].astype(np.float32)
lon = lon_full[j0:j1+1].astype(np.float32)
print('region lat %.4f..%.4f  lon %.4f..%.4f' % (lat[0], lat[-1], lon[0], lon[-1]))
# confirm neighbours are outside bounds
print('edge check: lat[403]=%.4f lat[464]=%.4f lon[558]=%.4f lon[619]=%.4f' %
      (lat_full[403], lat_full[464], lon_full[558], lon_full[619]))

time = tgt_dates.astype('datetime64[ns]')
ds = xr.Dataset(
    {'mhw': (('time','lat','lon'), mhw.astype(np.uint8))},
    coords={'time': time, 'lat': lat, 'lon': lon},
)
ds['mhw'].attrs.update({'long_name': 'marine heatwave (per-cell) mask', 'flag_values': np.array([0,1],dtype=np.uint8),
                        'flag_meanings': 'not_in_mhw in_mhw'})
os.makedirs('output', exist_ok=True)
enc = {'mhw': {'dtype': 'uint8', '_FillValue': None},
       'lat': {'dtype': 'float32'}, 'lon': {'dtype': 'float32'}}
ds.to_netcdf('output/mhw_mask.nc', engine='h5netcdf', encoding=enc)
print('wrote output/mhw_mask.nc')

# verify by reopening
chk = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
m2 = chk['mhw']
print('reopened: dims', dict(m2.sizes), 'dtype', m2.dtype)
print('sum', int(m2.values.sum()), 'time0', str(chk['time'].values[0])[:10], 'timeN', str(chk['time'].values[-1])[:10])
print('lat0/latN', float(chk['lat'][0]), float(chk['lat'][-1]), 'lon0/lonN', float(chk['lon'][0]), float(chk['lon'][-1]))
print('mask identical:', np.array_equal(m2.values, mhw.astype(np.uint8)))
chk.close()

events = [{'onset': '2009-06-26', 'end': '2009-07-05'}, {'onset': '2009-08-05', 'end': '2009-08-09'}]
report = {
    'region': {'lat_min': 61.57, 'lat_max': 62.77, 'lon_min': 20.17, 'lon_max': 21.37},
    'baseline_analysed': {'start': '1992-01-01', 'end': '2002-12-31'},
    'target_analysed': {'start': '2009-06-01', 'end': '2009-08-31'},
    'events': events,
    'complete': True,
    'caveats': ('Region cells are the dataset grid cells whose centres fall inside the bounds '
                '(nearest-cell alignment; 60x60 cells, 3308 finite on every target day, 292 land/ice cells masked 0). '
                'Pools for the ±5-day windows at the ends of the baseline include the extra days 1991-12-27..1991-12-31 '
                'and 2003-01-01..2003-01-05 as prescribed; day-of-year 60 (29 Feb) has no pool and was filled with the '
                'mean of days 59 and 61 before smoothing. All 4018 baseline-window and 92 target daily files were '
                'present, and each file time coordinate was verified against its filename. Thresholds, climatology, '
                'smoothing and comparisons computed in float64; 90th percentile via numpy method="hazen" '
                '(Hyndman-Fan type 5, MATLAB quantile default); centred 31-day moving mean verified against an '
                'explicit brute-force circular-window computation.')
}
with open('output/report.json','w') as f:
    json.dump(report, f, indent=2)
print('wrote output/report.json')
print(json.dumps(report, indent=2)[:1500])
