import os, json
import numpy as np
import xarray as xr

os.makedirs('output', exist_ok=True)
z = np.load('/work/sst_region.npz', allow_pickle=False)
mz = np.load('/work/mhw_intermediate.npz', allow_pickle=False)
mask = mz['mask']          # (92, n_sea) bool
sea = mz['sea']            # (60,60)
tgt_dates = [str(d) for d in mz['tgt_dates']]
lat = z['lat']; lon = z['lon']
print("mask shape:", mask.shape, "n sea:", int(sea.sum()))

M = np.zeros((len(tgt_dates), 60, 60), dtype=np.uint8)
M[:, sea] = mask.astype(np.uint8)
print("mask ones:", int(M.sum()))

active = M.max(axis=(1,2)).astype(bool)
events = []
i = 0
while i < len(active):
    if active[i]:
        s = i
        while i < len(active) and active[i]:
            i += 1
        events.append((tgt_dates[s], tgt_dates[i-1]))
    else:
        i += 1
print("events:", events)

time_vals = np.array(tgt_dates, dtype='datetime64[ns]')
ds_out = xr.Dataset(
    {'mhw': xr.DataArray(M, dims=('time', 'lat', 'lon'),
                          attrs={'long_name': 'Marine heatwave mask (1 = inside per-cell MHW, 0 otherwise)',
                                 'flag_values': np.array([0, 1], dtype=np.uint8),
                                 'flag_meanings': 'not in MHW; in MHW'})},
    coords={
        'time': xr.DataArray(time_vals, dims='time', attrs={'long_name': 'Time', 'standard_name': 'time', 'axis': 'T'}),
        'lat': xr.DataArray(lat, dims='lat', attrs={'long_name': 'latitude', 'units': 'degrees_north', 'standard_name': 'latitude', 'axis': 'Y'}),
        'lon': xr.DataArray(lon, dims='lon', attrs={'long_name': 'longitude', 'units': 'degrees_east', 'standard_name': 'longitude', 'axis': 'X'}),
    })
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("wrote output/mhw_mask.nc")

report = {
    "region": {"lat_min": 58.69, "lat_max": 59.89, "lon_min": 18.69, "lon_max": 19.89},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2010-06-01", "end": "2010-08-31"},
    "events": [{"onset": e[0], "end": e[1]} for e in events],
    "complete": True,
    "caveats": ""
}
with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2))
