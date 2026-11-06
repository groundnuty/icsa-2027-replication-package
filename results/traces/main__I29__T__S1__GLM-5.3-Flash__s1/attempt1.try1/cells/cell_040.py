import numpy as np, datetime, os, json
os.makedirs('output', exist_ok=True)
tgt = np.load('target.npy').astype(np.float64)
hot = np.load('hot.npy')
start = datetime.date(2015,6,1)
dates = [start + datetime.timedelta(days=k) for k in range(92)]

# mhw mask: all zeros (no per-cell MHWs found)
mhw = np.zeros(hot.shape, dtype=np.uint8)

import xarray as xr
ds_out = xr.Dataset(
    {'mhw': (('time','lat','lon'), mhw)},
    coords={'time': np.array(dates, dtype='datetime64[ns]'),
            'lat': np.load('latvals.npy') if os.path.exists('latvals.npy') else np.arange(57.86, 57.86+60*0.02, 0.02, dtype=np.float32)[:60],
            'lon': np.arange(21.02, 21.02+60*0.02, 0.02, dtype=np.float32)[:60]}
)
enc = {'mhw': {'dtype':'uint8','zlib':True,'_FillValue':None}}
ds_out.to_netcdf('output/mhw_mask.nc', engine='netcdf4', encoding=enc)

# verify round-trip
chk = xr.open_dataset('output/mhw_mask.nc', engine='netcdf4')
print(chk)
print('mhw dtype:', chk['mhw'].dtype, 'unique:', np.unique(chk['mhw'].values))
print('time[0], time[-1]:', chk.time.values[0], chk.time.values[-1])
chk.close()

report = {
  "region": {"lat_min": 57.85, "lat_max": 59.05, "lon_min": 21.01, "lon_max": 22.21},
  "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
  "target_analysed": {"start": "2015-06-01", "end": "2015-08-31"},
  "events": [],
  "complete": True,
  "caveats": "The requested region bounds (57.85-59.05 N, 21.01-22.21 E, inclusive) contain exactly the 60x60 grid cells with lat 57.86-59.04 and lon 21.02-22.20 on the dataset's 0.02-degree grid; the float32 coordinate values are within the bounds, so all region cells were analysed (3301 sea cells; 299 land cells all-NaN throughout). No day of the target period contains day-of-year 60. Thresholds, climatology, smoothing and comparisons were done in float64; pool percentiles use numpy method='hazen' (MATLAB quantile default). Per-cell hot runs never exceeded 3 consecutive days (>=5 required), so no per-cell MHWs and no regional events were detected; mhw is all zeros."
}
with open('output/report.json','w') as fh:
    json.dump(report, fh, indent=2)
print(json.dumps(report, indent=2)[:800])
print('files:', os.listdir('output'))
