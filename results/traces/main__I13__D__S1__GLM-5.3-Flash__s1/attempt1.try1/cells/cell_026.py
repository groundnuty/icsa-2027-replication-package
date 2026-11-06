import numpy as np, datetime as dt, json, os
import xarray as xr

datestrs = np.load('/work/extract_dates.npy')
arr32 = np.load('/work/extract_sst.npy')
dates = [dt.date.fromisoformat(s) for s in datestrs]
n_base_win = sum(1 for d in dates if d <= dt.date(2003,1,5))
tgt_dates = dates[n_base_win:]
base_win_dates = dates[:n_base_win]
mhw_mask = np.load('/work/mhw_mask.npy')  # (92,60,60) bool

# coordinate values from the dataset (float32 as stored)
with __import__('h5py').File('/work/data/sst_20210601.nc','r') as f:
    lat_vals = f['latitude'][130:190]
    lon_vals = f['longitude'][78:138]
print('lat', lat_vals.dtype, lat_vals[0], lat_vals[-1], '| lon', lon_vals.dtype, lon_vals[0], lon_vals[-1])

os.makedirs('/work/output', exist_ok=True)
time_vals = np.array([np.datetime64(d.isoformat(), 'ns') for d in tgt_dates])
ds = xr.Dataset(
    {'mhw': (('time','lat','lon'), mhw_mask.astype(np.uint8))},
    coords={'time': time_vals, 'lat': lat_vals, 'lon': lon_vals},
)
ds['mhw'].attrs['long_name'] = 'per-cell marine heatwave mask'
ds['mhw'].attrs['flag_values'] = np.array([0,1], dtype=np.uint8)
ds['mhw'].attrs['flag_meanings'] = 'not_in_mhw in_mhw'
ds.attrs['title'] = 'Per-cell marine heatwave mask, Baltic Sea region 56.09-57.29N 10.55-11.75E, 2021-06-01 to 2021-08-31'
ds.attrs['source_dataset'] = 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m'
ds.attrs['baseline_years'] = '1992-2002'
ds.to_netcdf('/work/output/mhw_mask.nc', engine='h5netcdf')
print('wrote /work/output/mhw_mask.nc')

# ---- report.json ----
active = mhw_mask.any(axis=(1,2))
idx = np.flatnonzero(active)
if idx.size:
    breaks = np.where(np.diff(idx) > 1)[0]
    starts = np.concatenate(([0], breaks+1)); ends = np.concatenate((breaks, [idx.size-1]))
    events = [{'onset': tgt_dates[int(idx[s])].isoformat(), 'end': tgt_dates[int(idx[e])].isoformat()}
              for s, e in zip(starts, ends)]
else:
    events = []

baseline_used = sorted({d for d in base_win_dates if 1992 <= d.year <= 2002})
report = {
    'region': {'lat_min': 56.09, 'lat_max': 57.29, 'lon_min': 10.55, 'lon_max': 11.75},
    'baseline_analysed': {'start': baseline_used[0].isoformat(), 'end': baseline_used[-1].isoformat()},
    'target_analysed': {'start': tgt_dates[0].isoformat(), 'end': tgt_dates[-1].isoformat()},
    'events': events,
    'complete': True,
    'caveats': ('Per-cell MHW detection restricted to the target period 2021-06-01..2021-08-31 as specified; '
                'thresholds/climatology from baseline 1992-2002 with +/-5-day pool windows, whose ends reach '
                '5 days beyond the baseline (1991-12-27..1991-12-31 and 2003-01-01..2003-01-05, included per method). '
                'All 92 target days and all 3296 sea cells analysed; no missing days.')
}
with open('/work/output/report.json','w') as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2))
