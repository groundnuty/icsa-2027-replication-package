import numpy as np, xarray as xr, json, os

m = np.load('/work/mhw.npz', allow_pickle=True)
mask = m['mask']          # (92, 60, 60) uint8
z = np.load('/work/interim.npz')
i0, i1 = int(z['t_i0']), int(z['t_i1'])

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
time_vals = ds.time.values[i0:i1]        # datetime64[ns], 92 values
lat_vals  = ds.latitude.values[z['li']]  # float32, 60
lon_vals  = ds.longitude.values[z['oi']] # float32, 60

out = xr.Dataset(
    data_vars={'mhw': (('time', 'lat', 'lon'), mask.astype(np.uint8))},
    coords={'time': time_vals, 'lat': lat_vals, 'lon': lon_vals},
    attrs={
        'title': 'Per-cell marine heatwave mask, Baltic Sea region 54.17-55.37N 13.25-14.45E, 2014-06-01 to 2014-08-31',
        'source': 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m (sst_s2.nc)',
        'comment': ('mhw=1 where the cell is inside a per-cell MHW (>=5 consecutive days with SST >= '
                    '90th-percentile threshold from 1992-2002 baseline, 31-day smoothed; runs separated by '
                    '<=2 non-hot days joined). Land cells are 0.'),
    },
)
os.makedirs('/work/output', exist_ok=True)
out.to_netcdf('/work/output/mhw_mask.nc')
print("wrote /work/output/mhw_mask.nc")

events = [{"onset": s, "end": e} for s, e in m['events'].tolist()]
report = {
    "region": {"lat_min": 54.17, "lat_max": 55.37, "lon_min": 13.25, "lon_max": 14.45},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2014-06-01", "end": "2014-08-31"},
    "events": events,
    "complete": True,
    "caveats": ("3303 of 3600 regional grid cells are sea cells (SST finite on every target day); the 297 land "
                "cells have no baseline data and are excluded (mhw=0). Every sea cell had a complete 121-value "
                "baseline pool for each day of year, so no missing-pool handling was needed. Thresholds are the "
                "Hazen (HF type 5) 90th percentile of the +/-5-day windows around 1992-2002 dates, day 60 set to "
                "the mean of days 59 and 61, then smoothed with a 31-day wrapping centred moving mean; all "
                "computations in float64. SST stored in kelvin."),
}
with open('/work/output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print("wrote /work/output/report.json")
print(json.dumps(report, indent=2))
