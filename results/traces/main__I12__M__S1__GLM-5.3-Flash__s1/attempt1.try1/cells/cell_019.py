import numpy as np, pickle, os, json
import xarray as xr

mhw = np.load('/tmp/mhw_mask.npy')       # (92, 60, 60) bool
with open('/tmp/percell.pkl','rb') as f:
    per_cell_events, td_list, ev, sea = pickle.load(f)
dates = np.load('/tmp/dates.npy')
tdates = dates[4028:]

print('mhw mask sum:', mhw.sum(), 'dtype bool -> uint8')
print('active days:', mhw.any(axis=(1,2)).sum())

os.makedirs('output', exist_ok=True)
# build NetCDF
ds = xr.Dataset(
    {'mhw': (('time','lat','lon'), mhw.astype('uint8'))},
    coords={'time': tdates.astype('datetime64[ns]'),
            'lat': np.array([56.09999847 + 0.02*i for i in range(60)], dtype='float32'),
            'lon': np.array([10.55999947 + 0.02*j for j in range(60)], dtype='float32')}
)
enc = {'mhw': {'dtype':'uint8', 'zlib':True, 'complevel':4}}
ds.to_netcdf('output/mhw_mask.nc', engine='netcdf4', encoding=enc)
print('wrote output/mhw_mask.nc')

report = {
  "region": {"lat_min": 56.09, "lat_max": 57.29, "lon_min": 10.55, "lon_max": 11.75},
  "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
  "target_analysed": {"start": "2009-06-01", "end": "2009-08-31"},
  "events": [{"onset": td_list[s], "end": td_list[e]} for s,e in ev],
  "complete": True,
  "caveats": ""
}
with open('output/report.json','w') as f:
    json.dump(report, f, indent=2)
print('wrote output/report.json')
print(json.dumps(report, indent=2))
