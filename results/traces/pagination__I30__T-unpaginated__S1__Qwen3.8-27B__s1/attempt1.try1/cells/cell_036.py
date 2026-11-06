
import sys, os, json, datetime as dt
import numpy as np
import xarray, fsspec
sys.path.insert(0,'/work/mhw')
import common

# dataset coordinate values
fs = fsspec.filesystem('onedata')
f = fs.open('/icsa2027_data_20261101T090944Z/s1z/sst_20100601.nc','rb')
ds = xarray.open_dataset(f, engine='h5netcdf')
lat_vals = ds['latitude'].values[260:320]   # float32, dataset values
lon_vals = ds['longitude'].values[485:545]
time_vals = ds['time'].values
ds.close(); f.close()
# sanity: compare with a baseline-year file
f2 = fs.open('/icsa2027_data_20261101T090944Z/s1z/sst_19960229.nc','rb')
ds2 = xarray.open_dataset(f2, engine='h5netcdf')
print('lat identical:', np.array_equal(lat_vals, ds2['latitude'].values[260:320]))
print('lon identical:', np.array_equal(lon_vals, ds2['longitude'].values[485:545]))
ds2.close(); f2.close()

mask = np.load('/work/mhw/mask.npy')          # (92, 3600)
tgt_dates = [dt.date(2010,6,1) + dt.timedelta(days=k) for k in range(92)]
times = np.array([d.toordinal() for d in tgt_dates], dtype='datetime64[D]')

mask3d = mask.reshape(92, 60, 60).astype(np.uint8)
ds_out = xarray.Dataset(
    data_vars={'mhw': (('time', 'lat', 'lon'), mask3d)},
    coords={'time': times, 'lat': ('lat', lat_vals), 'lon': ('lon', lon_vals)},
)
ds_out['mhw'].attrs['description'] = '1 where cell is inside a per-cell MHW on that day, 0 otherwise (land/missing cells 0)'
os.makedirs('/work/output', exist_ok=True)
ds_out.to_netcdf('/work/output/mhw_mask.nc', engine='netcdf4')
print('wrote /work/output/mhw_mask.nc')

report = {
    "region": {"lat_min": 58.69, "lat_max": 59.89, "lon_min": 18.69, "lon_max": 19.89},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2010-06-01", "end": "2010-08-31"},
    "events": [{"onset": "2010-06-29", "end": "2010-07-25"}],
    "complete": True,
    "caveats": ("3293 of 3600 region cells are sea cells (finite SST on all target days); 307 land/missing cells are 0. "
                "90th percentiles computed with numpy quantile method='hazen' as specified. All statistics in float64. "
                "One regional event found: 2010-06-29 to 2010-07-25 (27 consecutive active days; up to 3286 cells in MHW).")
}
with open('/work/output/report.json','w') as fh:
    json.dump(report, fh, indent=2)
print('wrote /work/output/report.json')
print(json.dumps(report, indent=2))
