import numpy as np, pickle, json, os
import xarray as xr

mask = np.load('/tmp/mhw_mask.npy')                    # (92, 3600) bool
t = np.load('/tmp/tgt.npz')
ttimes = t['times']
meta = pickle.load(open('/tmp/region_meta.pkl','rb'))
lat_vals = meta['lat_vals']   # float32, 60
lon_vals = meta['lon_vals']   # float32, 60

tgt = t['arr']
finite_tgt = np.all(np.isfinite(tgt), axis=0).reshape(3600)

m = mask.reshape(92, 60, 60).astype(np.uint8)
assert m.max() <= 1 and m.min() >= 0
assert not m[:, ~finite_tgt].any().any() == False  # land must be all zero
assert (m[:, ~finite_tgt].sum() == 0)

os.makedirs('output', exist_ok=True)
da = xr.DataArray(m, dims=('time','lat','lon'),
                  coords={'time': ttimes, 'lat': lat_vals, 'lon': lon_vals},
                  name='mhw')
da.to_netcdf('output/mhw_mask.nc')

events = [{"onset": "2009-06-24", "end": "2009-07-10"}]
report = {
    "region": {"lat_min": 56.09, "lat_max": 57.29, "lon_min": 10.55, "lon_max": 11.75},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": "2009-06-01", "end": "2009-08-31"},
    "events": events,
    "complete": True,
    "caveats": ""
}
with open('output/report.json','w') as f:
    json.dump(report, f, indent=2)
print('files written')
print(json.dumps(report, indent=2))