import os, json, datetime
import numpy as np, xarray as xr

print("cwd:", os.getcwd())
mask = np.load('/work/mask.npy')                      # (92, 3600) bool
lat  = np.load('/work/region_lat.npy')                # (60,) float32
lon  = np.load('/work/region_lon.npy')                # (60,) float32
ev   = np.load('/work/events.npy')
tgt_dates = [datetime.date(2009,6,1) + datetime.timedelta(days=k) for k in range(92)]
time_vals = np.array(tgt_dates, dtype='datetime64[ns]')

m3 = mask.reshape(92, 60, 60).astype(np.uint8)
out_dir = 'output'
os.makedirs(out_dir, exist_ok=True)
nc_path = os.path.join(out_dir, 'mhw_mask.nc')

ds_out = xr.Dataset(
    {'mhw': (('time', 'lat', 'lon'), m3)},
    coords={
        'time': ('time', time_vals),
        'lat':  ('lat', lat),
        'lon':  ('lon', lon),
    },
    attrs={'title': 'Per-cell marine heatwave mask, Baltic region 61.57-62.77N x 20.17-21.37E, 2009-06-01..2009-08-31',
           'source': 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m (sst_s2.nc), analysed_sst in kelvin',
           'comment': 'mhw=1 where cell is inside a per-cell MHW (>=5 consecutive days SST>=90th-pct threshold, gaps<=2 joined), 0 otherwise (land cells 0)'}
)
ds_out.to_netcdf(nc_path)
print("wrote", os.path.abspath(nc_path), os.path.getsize(nc_path), "bytes")

report = {
    "region": {"lat_min": 61.57, "lat_max": 62.77, "lon_min": 20.17, "lon_max": 21.37},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2009-06-01", "end": "2009-08-31"},
    "events": [{"onset": tgt_dates[int(s)].isoformat(), "end": tgt_dates[int(e)].isoformat()} for s, e in ev],
    "complete": True,
    "caveats": ("Sea cells = 3308 of 3600 region cells with finite SST on all 92 target days; 292 land cells set to 0. "
                "Threshold pools used baseline 1992-2002 dates plus the 5-day window extension days "
                "1991-12-27..1991-12-31 and 2003-01-01..2003-01-05; each pool has 121 dates. "
                "Thresholds = 90th percentile (numpy method='hazen', Hyndman-Fan type 5) of the pool; "
                "day-60 values set to mean of days 59 and 61; both then smoothed with a centred 31-day "
                "wrap-around moving mean; all computed in float64. Two regional events detected.")
}
rp = os.path.join(out_dir, 'report.json')
with open(rp, 'w') as f:
    json.dump(report, f, indent=2)
print("wrote", os.path.abspath(rp))
print(json.dumps(report, indent=2))
