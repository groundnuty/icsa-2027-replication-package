import numpy as np, pickle, json, os
import xarray as xr

d1 = pickle.load(open('/work/step1.pkl','rb'))
d3 = pickle.load(open('/work/step3.pkl','rb'))
mhw, ev, sea = d3['mhw'], d3['events'], d3['sea']
t_tgt, lat, lon = d1['t_tgt'], d1['lat'], d1['lon']

out_dir = os.path.join(os.getcwd(), 'output')
os.makedirs(out_dir, exist_ok=True)
print('cwd:', os.getcwd())

# mhw: (cells, 92) with cells = (lat,lon) row-major -> (time, lat, lon)
mhw_3d = mhw.T.reshape(len(t_tgt), len(lat), len(lon)).astype(np.uint8)
print('mhw_3d', mhw_3d.shape, mhw_3d.dtype, 'ones:', int(mhw_3d.sum()))
# land cells must be 0
land = ~sea
assert mhw_3d.reshape(-1, len(t_tgt))[land].sum() == 0

ds_out = xr.Dataset(
    {'mhw': (('time', 'lat', 'lon'), mhw_3d)},
    coords={'time': t_tgt, 'lat': lat, 'lon': lon},
)
ds_out['mhw'].encoding = {'dtype': 'uint8'}
ds_out.attrs = {'title': 'Marine heatwave mask, Baltic Sea region (lat 59.93-61.13N, lon 18.69-19.89E), 2009-06-01 to 2009-08-31',
                'source_dataset': 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m',
                'description': 'mhw=1 where the grid cell is inside a per-cell MHW (>=5 consecutive hot days, hot = SST >= smoothed 90th-percentile (hazen) day-of-year threshold from 1992-2002 baseline with +/-5-day windows, 31-day circular smoothing); gaps of 1-2 non-hot days merged. 0 otherwise (incl. land/missing cells).'}
ds_out.to_netcdf(os.path.join(out_dir, 'mhw_mask.nc'), engine='h5netcdf')

report = {
    'region': {'lat_min': 59.93, 'lat_max': 61.13, 'lon_min': 18.69, 'lon_max': 19.89},
    'baseline_analysed': {'start': '1991-12-27', 'end': '2003-01-05'},
    'target_analysed': {'start': '2009-06-01', 'end': '2009-08-31'},
    'events': [{'onset': str(ev[0][0])[:10], 'end': str(ev[0][1])[:10]} for ev in ev],
    'complete': True,
    'caveats': ('Region = 60x60 grid cells (lat 59.94-61.12N, lon 18.70-19.88E on the 0.02-deg grid) '
                'inside the inclusive bounds. SST in kelvin as stored. 1956 of 3600 cells were sea cells '
                '(finite SST on all 92 target days); land/missing cells are 0. Thresholds are the hazen '
                '(Hyndman-Fan type 5, 90th percentile) of the per-day-of-year pool of baseline days 1992-2002 '
                'with +/-5 calendar-day windows (pool dates 1991-12-27 to 2003-01-05, 121 days each), '
                'day-of-year 60 = mean of 59 and 61, then 31-day centred circular moving mean. '
                'Per-cell MHW = >=5 consecutive days with SST >= threshold, runs joined across 1-2 non-hot gaps; '
                'one regional event covering the whole target period.')
}
with open(os.path.join(out_dir, 'report.json'), 'w') as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2))

# verify written files
chk = xr.open_dataset(os.path.join(out_dir, 'mhw_mask.nc'), engine='h5netcdf')
print(chk)
print('mhw dtype:', chk['mhw'].dtype, 'unique:', np.unique(chk['mhw'].values))
print('time:', str(chk['time'].values[0])[:10], '->', str(chk['time'].values[-1])[:10], 'n=', chk.sizes['time'])
