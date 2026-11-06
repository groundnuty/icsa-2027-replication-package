import numpy as np, os, json, datetime as dt
import xarray as xr

z = np.load('data/climthr.npz')
res = np.load('data/results.npz')
mhw = res['mhw']; sea = z['sea']; lat = z['lat']; lon = z['lon']
dates = [dt.date(2009,6,1) + dt.timedelta(days=k) for k in range(92)]

# land cells all zero?
print('land total mhw days:', int(mhw[:, ~sea.ravel()].sum()) if False else int((mhw * ~sea[None, :]).sum()))
assert int((mhw * ~sea[None, :]).sum()) == 0
assert mhw.dtype == np.uint8 and mhw.shape == (92, 60, 60)
active = mhw.astype(bool).any(axis=(1,2))
events, i = [], 0
while i < 92:
    if active[i]:
        j = i
        while j+1 < 92 and active[j+1]: j += 1
        events.append((i, j)); i = j+1
    else: i += 1

os.makedirs('output', exist_ok=True)
time_vals = np.array(dates, dtype='datetime64[ns]')
ds = xr.Dataset(
    {'mhw': (('time', 'lat', 'lon'), mhw, {'long_name': 'Marine heatwave mask (1 = cell inside per-cell MHW, 0 = otherwise)'})},
    coords={'time': ('time', time_vals), 'lat': ('lat', lat.astype('float32')), 'lon': ('lon', lon.astype('float32'))},
    attrs={'source': 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m (version 202506)',
           'method': 'Baltic MHW catalogue method: 90th-percentile (hazen) threshold & climatology from 1992-2002 baseline pools (+/-5 days), 31-day wrap-around smoothing; MHW = >=5 consecutive hot days, gaps <=2 days joined; regional event = run of active days',
           'region': 'lat 56.09-57.29 N, lon 10.55-11.75 E'}
)
ds.to_netcdf('output/mhw_mask.nc', engine='netcdf4')

report = {
    "region": {"lat_min": 56.09, "lat_max": 57.29, "lon_min": 10.55, "lon_max": 11.75},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2009-06-01", "end": "2009-08-31"},
    "events": [{"onset": dates[s].isoformat(), "end": dates[e].isoformat()} for s, e in events],
    "complete": True,
    "caveats": ("All 92 target days and all baseline-window days (1991-12-27 to 2003-01-05, including the 5 days beyond the baseline ends) "
                "were available; all 3600 regional grid cells analysed, of which 3296 were sea cells (finite SST on every target day) and 304 land cells, "
                "set to 0. Threshold 90th percentile computed with numpy method='hazen' as specified in the task; note that MATLAB's true default "
                "('linear', Hyndman-Fan type 4) would shift the onset of the single regional event one day earlier (2009-06-23). "
                "SST compared in kelvin as stored; float64 used throughout.")
}
with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2))