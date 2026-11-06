import pickle, os, json
import numpy as np, xarray as xr, fsspec
from datetime import date

st = pickle.load(open('/tmp/stash.pkl','rb'))
mhw = st['mhw']; dts_t = st['dts_t']; Tt = st['Tt']; LA, LO = st['LA'], st['LO']
lat_sel = st['lat_sel']; lon_sel = st['lon_sel']

# exact dataset time coordinate values for the target days
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','rb')
ds = xr.open_dataset(f, engine='h5netcdf')
t = ds.time.values
tm = (t>=np.datetime64('2003-06-01'))&(t<=np.datetime64('2003-08-31'))
tvals = t[tm]
assert len(tvals)==Tt
assert all(a==b for a,b in zip(tvals.astype('datetime64[D]').astype(object), dts_t))
# confirm region coordinate values identical
mlat = (ds.latitude.values>=60.09)&(ds.latitude.values<=61.29)
mlon = (ds.longitude.values>=20.01)&(ds.longitude.values<=21.21)
assert np.array_equal(ds.latitude[mlat].values, lat_sel)
assert np.array_equal(ds.longitude[mlon].values, lon_sel)
ds.close(); f.close()

os.makedirs('output', exist_ok=True)
da = xr.DataArray(mhw, dims=('time','lat','lon'),
                  coords={'time': tvals, 'lat': lat_sel, 'lon': lon_sel},
                  name='mhw').astype(np.uint8)
da.to_dataset().to_netcdf('output/mhw_mask.nc')

report = {
  "region": {"lat_min": 60.09, "lat_max": 61.29, "lon_min": 20.01, "lon_max": 21.21},
  "baseline_analysed": {"start": st['used_min'], "end": st['used_max']},
  "target_analysed": {"start": st['target_min'], "end": st['target_max']},
  "events": [{"onset": e[0], "end": e[1]} for e in st['events']],
  "complete": True,
  "caveats": ("Region grid cells: 60x60 on the 0.02 deg product grid; 3287 sea cells had finite SST on all 92 target days, "
              "the other 313 land/masked cells are set to 0. Thresholds/climatology per day of year (1..366, 29 Feb=60, "
              "no day 60 in non-leap years) from baseline 1992-2002 pools of all SST within +/-5 calendar days of baseline "
              "dates with that day of year, including the 5-day extensions beyond the baseline ends (1991-12-27..1991-12-31 "
              "and 2003-01-01..2003-01-05); all pools had exactly 121 values. Threshold = 90th percentile (numpy "
              "method='hazen', Hyndman-Fan type 5) and climatology = mean, NaN ignored; day 60 set to the mean of days 59 "
              "and 61; each then smoothed with an unweighted centred 31-day moving mean wrapping the 366-day year. Hot day: "
              "SST (K) >= threshold. Per-cell MHW: >=5 consecutive hot days; MHWs separated by 1-2 non-hot days joined with "
              "gap days included. One regional event detected: 2003-07-15 to 2003-08-08 (all 3287 sea cells were inside a "
              "per-cell MHW on 2003-07-27 through 2003-08-05).")
}
with open('output/report.json','w') as fh:
    json.dump(report, fh, indent=2)
print('written')

# ---- verify by reading back ----
chk = xr.open_dataset('output/mhw_mask.nc')
print(chk)
print('mhw dtype', chk.mhw.dtype, 'dims', dict(chk.sizes))
print('time first/last', chk.time.values[0], chk.time.values[-1])
print('lat first/last', float(chk.lat.values[0]), float(chk.lat.values[-1]))
print('lon first/last', float(chk.lon.values[0]), float(chk.lon.values[-1]))
print('mhw sum', int(chk.mhw.values.sum()), 'max', int(chk.mhw.values.max()))
print('report:', json.load(open('output/report.json'))['events'])
import os
for fn in ['output/mhw_mask.nc','output/report.json']:
    print(fn, os.path.getsize(fn), 'bytes')
