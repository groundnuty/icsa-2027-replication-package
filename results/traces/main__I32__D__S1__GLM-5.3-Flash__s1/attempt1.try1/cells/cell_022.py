import numpy as np, json, os, h5py
from datetime import date, timedelta

os.makedirs('/work/output', exist_ok=True)
mask = np.load('/work/mhw_mask.npy')          # (92,60,60) bool
meta = json.load(open('/work/meta.json'))
events = json.load(open('/work/events.json'))
t0 = date.fromisoformat(meta['t0']); t1 = date.fromisoformat(meta['t1'])
nt = (t1-t0).days+1
tdates = [t0+timedelta(days=i) for i in range(nt)]
tsecs = np.array(meta['time_secs_target'], dtype=np.int32)
lat = np.array(meta['lat_vals'], dtype=np.float32)
lon = np.array(meta['lon_vals'], dtype=np.float32)
mhw = mask.astype(np.uint8)

with h5py.File('/work/output/mhw_mask.nc', 'w') as f:
    f.createDimension('time', nt)
    f.createDimension('lat', len(lat))
    f.createDimension('lon', len(lon))
    tv = f.create_dataset('time', data=tsecs, dtype='int32')
    tv.attrs['units'] = 'seconds since 1981-01-01'
    tv.attrs['calendar'] = 'proleptic_gregorian'
    tv.attrs['standard_name'] = 'time'
    tv.attrs['axis'] = 'T'
    yv = f.create_dataset('lat', data=lat, dtype='float32')
    yv.attrs['units'] = 'degrees_north'
    yv.attrs['standard_name'] = 'latitude'
    yv.attrs['axis'] = 'Y'
    xv = f.create_dataset('lon', data=lon, dtype='float32')
    xv.attrs['units'] = 'degrees_east'
    xv.attrs['standard_name'] = 'longitude'
    xv.attrs['axis'] = 'X'
    mv = f.create_dataset('mhw', data=mhw, dtype='uint8', chunks=(min(nt,30), len(lat), len(lon)))
    mv.attrs['_FillValue'] = np.uint8(0)
    mv.attrs['long_name'] = 'per-cell marine heatwave mask (1 = cell inside a per-cell MHW, 0 otherwise; land = 0)'
    f.attrs['title'] = 'Marine heatwave mask, Baltic Sea region, 2005-06-01 to 2005-08-31'
    f.attrs['source_dataset'] = 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m'
    f.attrs['region_lat_min'] = 59.05; f.attrs['region_lat_max'] = 60.25
    f.attrs['region_lon_min'] = 21.25; f.attrs['region_lon_max'] = 22.45

report = {
    "region": {"lat_min": 59.05, "lat_max": 60.25, "lon_min": 21.25, "lon_max": 22.45},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2005-06-01", "end": "2005-08-31"},
    "events": [{"onset": tdates[s].isoformat(), "end": tdates[e].isoformat()} for s, e in events],
    "complete": True,
    "caveats": ("Baseline pools include the +/-5-day extension days beyond the 1992-2002 baseline years "
                "(1991-12-27 to 1991-12-31 and 2003-01-01 to 2003-01-05) as specified; day-of-year 60 (29 February) "
                "has no pool of its own and, after percentile/mean computation, was filled as the mean of days 59 and 61 "
                "before smoothing. Dataset version 202506.")
}
with open('/work/output/report.json', 'w') as fh:
    json.dump(report, fh, indent=2)
print(json.dumps(report, indent=2))
print("files:", os.listdir('/work/output'))
