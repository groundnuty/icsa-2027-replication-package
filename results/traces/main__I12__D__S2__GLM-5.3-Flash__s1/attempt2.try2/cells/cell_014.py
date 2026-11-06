import numpy as np, xarray as xr, json, os

ds = xr.open_dataset('/work/s2z/sst_s2.nc', engine='h5netcdf')
t = ds.time.values
lat = ds.latitude.values; lon = ds.longitude.values
lat_idx = np.where((lat >= 56.09) & (lat <= 57.29))[0]
lon_idx = np.where((lon >= 10.55) & (lon <= 11.75))[0]
idx = np.load('/work/idx.npz'); j0, j1 = int(idx['j0']), int(idx['j1'])

m = np.load('/work/mhw_state.npz')
mhw = m['mhw']            # (92, 60, 60) bool
print('mhw mask shape', mhw.shape, 'sum', int(mhw.sum()))

os.makedirs('/work/output', exist_ok=True)
out = xr.Dataset(
    {'mhw': (('time', 'lat', 'lon'), mhw.astype(np.uint8))},
    coords={
        'time': t[j0:j1],
        'lat': lat[lat_idx].astype(np.float32),
        'lon': lon[lon_idx].astype(np.float32),
    },
)
out['mhw'].encoding = {'dtype': 'uint8', '_FillValue': None}
out.to_netcdf('/work/output/mhw_mask.nc', engine='h5netcdf')
print('wrote mhw_mask.nc', os.path.getsize('/work/output/mhw_mask.nc'), 'bytes')

report = {
    "region": {"lat_min": 56.09, "lat_max": 57.29, "lon_min": 10.55, "lon_max": 11.75},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2009-06-01", "end": "2009-08-31"},
    "events": [{"onset": "2009-06-24", "end": "2009-07-10"}],
    "complete": True,
    "caveats": "Baseline pool windows per the prescribed method extend 5 calendar days beyond the 1992-2002 baseline ends (1991-12-27 to 1991-12-31 and 2003-01-01 to 2003-01-05); those values entered the day-of-year pools and are noted here because baseline_analysed reports only the 1992-2002 baseline itself. Sea cells (3296 of 3600 region cells) are those with finite SST on every target day; land cells have mhw=0. Dataset: cmems_obs-sst_bal_phy-temp_my_l4_P1D-m version 202506 (SST_BAL_SST_L4_REP_OBSERVATIONS_010_016), SST in kelvin as stored."
}
with open('/work/output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2))