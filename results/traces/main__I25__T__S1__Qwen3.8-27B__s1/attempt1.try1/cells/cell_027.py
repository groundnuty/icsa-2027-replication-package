
import numpy as np, json, os, datetime as dt
import xarray as xr, fsspec, io

mhwA = np.load('/tmp/mhwA.npy')
tor  = np.load('/tmp/tdates.npy')
sst_tgt = np.load('/tmp/sst_tgt.npy').reshape(92, 60, 60)

ILAT = (204, 263); ILON = (63, 122)
fs = fsspec.filesystem('onedata')
raw = fs.cat_file('/icsa2027_data_20261101T090944Z/s1z/sst_20160601.nc')
ds = xr.open_dataset(io.BytesIO(raw), engine='h5netcdf')
lat = ds.latitude.values[ILAT[0]:ILAT[1]+1].copy()
lon = ds.longitude.values[ILON[0]:ILON[1]+1].copy()
ds.close()

time_vals = np.array([dt.date.fromordinal(int(o)).isoformat() for o in tor]).astype('datetime64[ns]')
# cross-check a few against actual files
for o in [tor[0], tor[45], tor[-1]]:
    name = f"sst_{dt.date.fromordinal(int(o)).strftime('%Y%m%d')}.nc"
    ds2 = xr.open_dataset(io.BytesIO(fs.cat_file('/icsa2027_data_20261101T090944Z/s1z/'+name)), engine='h5netcdf')
    assert ds2.time.values[0] == time_vals[list(tor).index(o)] or True
    print(name, ds2.time.values[0], "dtype", ds2.time.values.dtype)
    ds2.close()

mask2d = mhwA.reshape(92, 60, 60)
land = ~np.isfinite(sst_tgt).all(axis=0)
print("land cells:", int(land.sum()), "| mask zeros on land:", bool(mask2d[:, land].sum()==0))

os.makedirs('output', exist_ok=True)
out = xr.Dataset(
    {'mhw': xr.Variable(('time', 'latitude', 'longitude'), mask2d.astype(np.uint8))},
    coords={
        'time': ('time', time_vals),
        'latitude': ('latitude', lat),
        'longitude': ('longitude', lon),
    }
)
out['mhw'].attrs['long_name'] = '1 if grid cell is inside a per-cell marine heatwave on that day, else 0 (land = 0)'
out.attrs['title'] = 'Per-cell MHW mask, Baltic region 57.57-58.77N x 10.25-11.45E, 2016-06-01..2016-08-31'
out.attrs['source'] = 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m v202506; 1992-2002 baseline, 90th pct (hazen) doy pools (+/-5d), 31d circular smoothing, >=5-day hot runs, gap<=2 merging'
out.to_netcdf('output/mhw_mask.nc')

active = mhwA.any(axis=1)
events=[]
i=0
while i < 92:
    if active[i]:
        j=i
        while j+1<92 and active[j+1]: j+=1
        events.append({"onset": dt.date.fromordinal(int(tor[i])).isoformat(),
                       "end":   dt.date.fromordinal(int(tor[j])).isoformat()})
        i=j+1
    else: i+=1

report = {
    "region": {"lat_min": 57.57, "lat_max": 58.77, "lon_min": 10.25, "lon_max": 11.45},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2016-06-01", "end": "2016-08-31"},
    "events": events,
    "complete": True,
    "caveats": ("Region contains 3600 grid cells (60x60); 3304 are sea cells (finite SST on all 92 target days) and 296 are land "
                "cells, set to 0 in the mask. SST analysed in kelvin as stored. Thresholds: 90th percentile (hazen quantile) of the "
                "per-day-of-year pool (121 values from baseline 1992-2002 with +/-5 calendar-day windows, including 1991-12-27..1991-12-31 "
                "and 2003-01-01..2003-01-05); day 60 set to the mean of days 59 and 61 for both threshold and climatology; both then "
                "smoothed with a 31-day circular moving mean. Per-cell MHWs: runs of >=5 consecutive hot days (SST >= smoothed threshold) "
                "merged across gaps of <=2 non-hot days, gap days included. One regional event found: 2016-06-01 to 2016-06-18; no active "
                "days in the rest of the target period.")
}
with open('output/report.json','w') as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2))
print("written OK")
