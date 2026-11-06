import numpy as np, json, os
import xarray as xr, fsspec

mask = np.load('/tmp/mask_flat.npy').reshape(92, 60, 60)

fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine="h5netcdf")
lat = ds.latitude.values.astype('float64'); lon = ds.longitude.values.astype('float64')
li = np.nonzero((lat>=59.05)&(lat<=60.25))[0]; lj = np.nonzero((lon>=21.25)&(lon<=22.45))[0]
lat32 = ds.latitude.values[li]
lon32 = ds.longitude.values[lj]
tvals = ds.time.values[11839:11931]
time_units = 'seconds since 1981-01-01'
os.makedirs('output', exist_ok=True)

da = xr.DataArray(mask.astype(np.uint8), dims=('time','latitude','longitude'),
                  coords={'time': ('time', tvals), 'latitude': ('latitude', lat32), 'longitude': ('longitude', lon32)},
                  name='mhw', attrs={'long_name':'marine heatwave mask: 1 if cell is inside a per-cell MHW on that day, 0 otherwise (land=0)'})
ds_out = da.to_dataset()
ds_out.to_netcdf('output/mhw_mask.nc', encoding={'time': {'units': time_units}})
print('wrote mhw_mask.nc')

events = [{"onset": "2014-07-19", "end": "2014-08-20"}]
report = {
  "region": {"lat_min": 59.05, "lat_max": 60.25, "lon_min": 21.25, "lon_max": 22.45},
  "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
  "target_analysed": {"start": "2014-06-01", "end": "2014-08-31"},
  "events": events,
  "complete": True,
  "caveats": "310 of 3600 region cells lack finite SST on some target days (land) and are set to 0. Baseline pools use 1991-12-27 to 2003-01-05 to cover the +/-5-day windows around the 1992-2002 baseline edges; NaN values in baseline pools ignored per method. Day-of-year mapped by month/day in the leap-year calendar (Mar 1 = 61, Dec 31 = 366); thresholds are Hazen (Hyndman-Fan type 5) 90th percentiles."
}
with open('output/report.json', 'w') as fh:
    json.dump(report, fh, indent=2)
print('wrote report.json')

# ---- verification read-back ----
chk = xr.open_dataset('output/mhw_mask.nc')
print(chk)
m = chk.mhw.values
print('dtype', m.dtype, 'shape', m.shape)
print('total 1s:', int(m.sum()), 'active days:', int(m.any(axis=(1,2)).sum()))
print('time first/last:', chk.time.values[0], chk.time.values[-1])
print('lat first/last:', chk.latitude.values[0], chk.latitude.values[-1])
print('lon first/last:', chk.longitude.values[0], chk.longitude.values[-1])
flat = np.load('/tmp/mask_flat.npy')
print('matches flat mask:', bool((m.reshape(92,-1) == flat).all()))
print(open('output/report.json').read())
