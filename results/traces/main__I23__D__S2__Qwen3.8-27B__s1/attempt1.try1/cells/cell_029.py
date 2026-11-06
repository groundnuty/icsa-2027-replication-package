import os, json
import numpy as np
import pickle
import xarray as xr

print("cwd:", os.getcwd())
with open('/work/final.pkl','rb') as f:
    F = pickle.load(f)
with open('/work/data.pkl','rb') as f:
    D = pickle.load(f)

mask = F['mask']                 # (3600, 92) uint8
time_tgt = F['time_tgt']         # (92,) datetime64[ns]
lat_full, lon_full = D['lat'], D['lon']
lat_r = lat_full[196:256]
lon_r = lon_full[485:545]
print("mask:", mask.shape, mask.dtype, "sum:", int(mask.sum()))
print("lat_r:", lat_r[0], lat_r[-1], lat_r.dtype, " lon_r:", lon_r[0], lon_r[-1], lon_r.dtype)
print("time:", time_tgt[0], time_tgt[-1], time_tgt.dtype)
assert mask.shape == (3600, 92)

# build (time, lat, lon) array
arr = np.zeros((92, 60, 60), dtype=np.uint8)
arr[:, :, :] = 0
m3 = mask.reshape(60, 60, 92).transpose(2, 0, 1)
arr = m3.astype(np.uint8)
assert arr.sum() == 5

ds_out = xr.Dataset(
    {'mhw': xr.DataArray(arr, dims=('time','lat','lon'))},
    coords={'time': ('time', time_tgt),
            'lat': ('lat', lat_r),
            'lon': ('lon', lon_r)}
)
ds_out['mhw'].encoding = {'dtype': 'uint8'}
ds_out.attrs = {'source': 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m (sst_s2.nc), analysed_sst',
                'title': 'Per-cell marine heatwave mask, region 57.41-58.61N 18.69-19.89E, 2013-06-01..2013-08-31',
                'method': '90th-pct (hazen) day-of-year threshold from 1992-2002 baseline, +/-5d windows, '
                          '31-day wrap-around smoothed; MHW = >=5 consecutive hot days, gaps <=2 joined; '
                          'SST >= threshold (kelvin)'}
outdir = 'output'
os.makedirs(outdir, exist_ok=True)
ds_out.to_netcdf(os.path.join(outdir, 'mhw_mask.nc'))
print("wrote", os.path.join(outdir, 'mhw_mask.nc'), "size:", os.path.getsize(os.path.join(outdir,'mhw_mask.nc')))

report = {
    "region": {"lat_min": 57.41, "lat_max": 58.61, "lon_min": 18.69, "lon_max": 19.89},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2013-06-01", "end": "2013-08-31"},
    "events": [{"onset": e[0], "end": e[1]} for e in F['events']],
    "complete": True,
    "caveats": ("3309 of 3600 region cells were sea cells (finite SST on all 92 target days). "
                "In 2013-06-01..2013-08-31 SST in this Gulf of Riga region was generally about 2 K "
                "below the 1992-2002 90th-percentile day-of-year thresholds, so only one per-cell "
                "MHW was found: 2013-06-09..2013-06-13 in a single grid cell (57.64N, 18.80E), "
                "giving one 5-day regional event.")
}
with open(os.path.join(outdir, 'report.json'), 'w') as f:
    json.dump(report, f, indent=2)
print("wrote report.json")
print(json.dumps(report, indent=2))
