import json, datetime as dt
import numpy as np
import xarray as xr

# region grid (dataset coordinate values, float32 as stored)
import h5py
base = "/data/icsa2027_data_20261101T090944Z/s1z"
with h5py.File(f"{base}/sst_20120701.nc", 'r') as f:
    lat_all = f['latitude'][:].astype(np.float32)
    lon_all = f['longitude'][:].astype(np.float32)
lat = lat_all[np.logical_and(lat_all >= 60.09, lat_all <= 61.29)]
lon = lon_all[np.logical_and(lon_all >= 20.01, lon_all <= 21.21)]
assert lat.shape == (60,) and lon.shape == (60,)

def daterange(a, b):
    d, out = a, []
    while d <= b:
        out.append(d); d += dt.timedelta(days=1)
    return out
tgt_dates = daterange(dt.date(2012,6,1), dt.date(2012,8,31))
time_vals = np.array([d.isoformat() for d in tgt_dates], dtype='datetime64[ns]')

sea = np.load('/work/chk/sea.npy')
# mhw mask: all zeros (no per-cell MHWs found); keep shape (time, lat, lon)
mhw = np.zeros((92, 60, 60), dtype=np.uint8)

ds = xr.Dataset(
    {'mhw': (('time', 'lat', 'lon'), mhw)},
    coords={'time': ('time', time_vals), 'lat': ('lat', lat), 'lon': ('lon', lon)},
)
ds.to_netcdf('output/mhw_mask.nc')

report = {
    "region": {"lat_min": 60.09, "lat_max": 61.29, "lon_min": 20.01, "lon_max": 21.21},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2012-06-01", "end": "2012-08-31"},
    "events": [],
    "complete": True,
    "caveats": ("Threshold pools use the prescribed +/-5-day windows, extending the 1992-2002 baseline to "
                "1991-12-27..2003-01-05; 90th percentile computed with numpy quantile method='hazen' "
                "(Hyndman-Fan type 5), day-60 value set to mean of days 59/61, then both fields smoothed "
                "with a wrapped 31-day centred moving mean. 313 of 3600 regional cells were excluded as "
                "non-sea cells (SST missing on at least one target day). The warmest 2012 signal "
                "(3 consecutive hot days Aug 17-19 in a few northern cells) did not reach the 5-day "
                "MHW minimum, so no per-cell MHWs and no regional events were detected; the mask is all zero."),
}
with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

# verify outputs
chk = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(chk)
print("mhw dtype:", chk['mhw'].dtype, "sum:", int(chk['mhw'].values.sum()))
print("time range:", chk['time'].values[0], "..", chk['time'].values[-1], "n:", chk['time'].size)
print("lat range:", float(chk['lat'].values[0]), "..", float(chk['lat'].values[-1]))
print("lon range:", float(chk['lon'].values[0]), "..", float(chk['lon'].values[-1]))
chk.close()
print(open('output/report.json').read())
