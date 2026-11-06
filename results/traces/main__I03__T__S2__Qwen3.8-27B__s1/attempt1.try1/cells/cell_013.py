import numpy as np, json, os, fsspec, xarray as xr
os.makedirs('output', exist_ok=True)
st = np.load('/tmp/mhw_state.npz')
cellmhw, sea, hot, thr_s = st['cellmhw'], st['sea'], st['hot'], st['thr_s']
NC = cellmhw.shape[1]
assert cellmhw.shape == (92, 3600)
assert int(cellmhw[:, ~sea].sum()) == 0, 'non-sea cells must be 0'

fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','rb')
ds = xr.open_dataset(f, engine="h5netcdf")
t = ds['time'].values
lat = ds['latitude'].values.astype(np.float64); lon = ds['longitude'].values.astype(np.float64)
li = np.where((lat>=54.17)&(lat<=55.37))[0]; lo = np.where((lon>=13.25)&(lon<=14.45))[0]
tb0 = np.searchsorted(t, np.datetime64('2014-06-01')); tb1 = np.searchsorted(t, np.datetime64('2014-08-31'))
time_vals = t[tb0:tb1+1]
lat_vals = ds['latitude'].values[li]   # keep original float32 values
lon_vals = ds['longitude'].values[lo]
print('coords:', time_vals[0], '->', time_vals[-1], time_vals.size, '| lat', lat_vals[0], '->', lat_vals[-1], '| lon', lon_vals[0], '->', lon_vals[-1])

mhw = cellmhw.reshape(92, len(li), len(lo)).astype(np.uint8)
out = xr.Dataset(
    data_vars={'mhw': (('time','lat','lon'), mhw)},
    coords={'time': ('time', time_vals), 'lat': ('lat', lat_vals), 'lon': ('lon', lon_vals)})
out['mhw'].attrs['description'] = '1 where the cell is inside a per-cell marine heatwave on that day, 0 otherwise (land cells 0); Baltic region 54.17-55.37N, 13.25-14.45E; 2014-06-01..2014-08-31'
try:
    out.to_netcdf('output/mhw_mask.nc', engine='netcdf4')
    eng = 'netcdf4'
except Exception as ex:
    print('netcdf4 failed:', ex)
    out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
    eng = 'h5netcdf'
print('wrote output/mhw_mask.nc with engine', eng)

events = json.load(open('/tmp/events.json'))
report = {
  "region": {"lat_min": 54.17, "lat_max": 55.37, "lon_min": 13.25, "lon_max": 14.45},
  "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
  "target_analysed": {"start": "2014-06-01", "end": "2014-08-31"},
  "events": [{"onset": o, "end": e} for o, e in events],
  "complete": True,
  "caveats": ("baseline_analysed includes the 5-day window extensions beyond the 1992-2002 baseline "
              "(1991-12-27 to 2003-01-05) that the method includes in the pools of the first/last days; "
              "day 60 pools are empty by construction and its threshold/climatology was set to the mean of days 59 and 61 before 31-day wrap-around smoothing. "
              "Thresholds computed with numpy nanquantile(method='hazen') and nanmean on float64, as specified. "
              "Per-cell MHWs are runs of >=5 hot days (SST >= threshold) merged when separated by <=2 days; regional events are maximal runs of days with at least one cell in an MHW.")
}
with open('output/report.json','w') as fh:
    json.dump(report, fh, indent=2)
print(json.dumps(report, indent=2))
ds.close(); f.close()
