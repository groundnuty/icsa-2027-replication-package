import numpy as np, json, os
import xarray as xr, fsspec

mask = np.load('/tmp/mask_flat.npy').reshape(92, 60, 60)
tdates = np.load('/tmp/tdates.npy')

fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine="h5netcdf")
lat = ds.latitude.values.astype('float64'); lon = ds.longitude.values.astype('float64')
li = np.nonzero((lat>=59.05)&(lat<=60.25))[0]; lj = np.nonzero((lon>=21.25)&(lon<=22.45))[0]
lat32 = ds.latitude.values[li]   # exact float32 values
lon32 = ds.longitude.values[lj]
tvals = ds.time.values[11839:11931]  # datetime64[ns]
time_units = ds.time.encoding.get('units')
print('time units:', time_units, 'first/last:', tvals[0], tvals[-1])
print('lat32', lat32[0], lat32[-1], 'lon32', lon32[0], lon32[-1])

os.makedirs('output', exist_ok=True)
da = xr.DataArray(mask.astype(np.uint8), dims=('time','latitude','longitude'),
                  coords={'time': ('time', tvals), 'latitude': ('latitude', lat32), 'longitude': ('longitude', lon32)},
                  name='mhw', attrs={'long_name':'marine heatwave mask: 1 if cell is inside a per-cell MHW on that day, 0 otherwise (land=0)'})
da.time.attrs['units'] = time_units
ds_out = da.to_dataset()
ds_out.to_netcdf('output/mhw_mask.nc')
print('wrote mhw_mask.nc')

events = [{"onset": "2014-07-19", "end": "2014-08-20"}]
report = {
  "region": {"lat_min": 59.05, "lat_max": 60.25, "lon_min": 21.25, "lon_max": 22.45},
  "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
  "target_analysed": {"start": "2014-06-01", "end": "2014-08-31"},
  "events": events,
  "complete": True,
  "caveats": "310 of 3600 region cells lack finite SST on some target days (land) and are set to 0. Baseline pools use 1991-12-27 to 2003-01-05 to cover the +/-5-day windows around the 1992-2002 baseline edges; NaN values in baseline pools ignored per method. Day-of-year mapped by month/day in leap-year calendar (Mar 1 = 61, Dec 31 = 366)."
}
with open('output/report.json', 'w') as fh:
    json.dump(report, fh, indent=2)
print('wrote report.json')
