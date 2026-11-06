
import numpy as np, pandas as pd, json, os, time
import xarray as xr, fsspec
t0 = time.time()
in_mhw = np.load('/tmp/mhw/in_mhw.npy')          # (92, 3600) uint8, cell idx = ilat*60 + ilon
td = pd.to_datetime(np.load('/tmp/mhw/tgt_dates.npy'), unit='D')
lat = np.load('/tmp/mhw/lat.npy'); lon = np.load('/tmp/mhw/lon.npy')
print("mask ones:", int(in_mhw.sum()), "of", in_mhw.size)

# get source time CF encoding
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
src = xr.open_dataset(f, engine='h5netcdf')
tenc = dict(src['time'].encoding)
tatt = dict(src['time'].attrs)
print("src time encoding:", tenc)
print("src time attrs:", tatt)
src.close(); f.close()

os.makedirs('output', exist_ok=True)
mhw3 = in_mhw.reshape(92, 60, 60)
times = td.to_numpy()
ds_out = xr.Dataset(
    data_vars={'mhw': (('time', 'lat', 'lon'), mhw3.astype(np.uint8))},
    coords={
        'time': ('time', times, tatt),
        'lat': ('lat', lat),
        'lon': ('lon', lon),
    },
)
enc = {}
if tenc:
    u = tenc.get('units')
    if u:
        enc['time'] = {'units': u}
        if 'calendar' in tenc:
            enc['time']['calendar'] = tenc['calendar']
ds_out.to_netcdf('output/mhw_mask.nc', encoding=enc or None)
print("wrote mhw_mask.nc %.1fs" % (time.time()-t0))

report = {
    "region": {"lat_min": 54.45, "lat_max": 55.65, "lon_min": 16.05, "lon_max": 17.25},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2021-06-01", "end": "2021-08-31"},
    "events": [{"onset": "2021-06-01", "end": "2021-08-08"}],
    "complete": True,
    "caveats": ("All 92 target days and the full 1991-12-27 to 2003-01-05 baseline window (1992-2002 baseline plus 5-day edge extensions) "
                "were present in the dataset. 308 land cells of the 3600 region cells have no finite SST on any target day and are reported as 0. "
                "Thresholds: per day-of-year (366-day mapping, 31 Dec = 366 in all years, 29 Feb = 60) 90th percentile of the 121-value pool "
                "(baseline dates 1992-2002 +/- 5 days), Hyndman-Fan type 5 (numpy hazen), NaN-ignored; 29 Feb filled from mean of 28 Feb and 1 Mar; "
                "then a 31-day centred circular moving mean. MHWs: runs of >=5 consecutive days with SST >= threshold, joining gaps of 1-2 days."),
}
with open('output/report.json', 'w') as fh:
    json.dump(report, fh, indent=2)
print("wrote report.json")

# ---- verify written files
chk = xr.open_dataset('output/mhw_mask.nc')
print(chk)
print("mhw dtype:", chk['mhw'].dtype, "dims:", dict(chk.sizes))
print("time:", pd.DatetimeIndex(chk['time'].values)[0], "->", pd.DatetimeIndex(chk['time'].values)[-1])
print("lat range:", float(chk['lat'].values.min()), float(chk['lat'].values.max()))
print("lon range:", float(chk['lon'].values.min()), float(chk['lon'].values.max()))
print("ones in file:", int(np.asarray(chk['mhw']).sum()))
# per-day active pattern check
m = np.asarray(chk['mhw'])
act = (m.sum(axis=(1, 2)) > 0)
days = pd.DatetimeIndex(chk['time'].values)
run_starts = [str(days[i].date()) for i in range(92) if act[i] and (i == 0 or not act[i-1])]
run_ends = [str(days[i].date()) for i in range(92) if act[i] and (i == 91 or not act[i+1])]
print("event starts:", run_starts, "event ends:", run_ends)
chk.close()
print(json.dumps(report, indent=1)[:600])
print("done %.1fs" % (time.time()-t0))
