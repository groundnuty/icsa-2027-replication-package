import os, json, numpy as np, xarray as xr, warnings
warnings.filterwarnings('ignore')
print('cwd:', os.getcwd())
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
d64 = ds['time'].values.astype('datetime64[D]')
def ix(y,m,d): return int((np.datetime64(f'{y:04d}-{m:02d}-{d:02d}') - d64[0]).astype(np.int64))
glo, ghi = ix(2015,6,1), ix(2015,8,31)

zg = np.load('/work/diag.npz')
mask3 = zg['mask']              # (92, 60, 60) uint8
active = zg['active']
mhw3 = mask3.astype(np.uint8)
assert mhw3.dtype == np.uint8 and mhw3.shape == (92, 60, 60)

out_dir = '/work/output'
os.makedirs(out_dir, exist_ok=True)
time_v = ds['time'].isel(time=slice(glo, ghi+1)).values
lat_v = ds['latitude'].isel(latitude=slice(132, 192)).values
lon_v = ds['longitude'].isel(longitude=slice(436, 496)).values

dsm = xr.Dataset(
    {'mhw': (('time', 'latitude', 'longitude'), mhw3)},
    coords={'time': time_v, 'latitude': lat_v, 'longitude': lon_v},
    attrs={'title': 'Per-cell marine heatwave (MHW) mask, Baltic Sea region',
           'region': 'lat 56.13-57.33 N, lon 17.71-18.91 E (inclusive bounds)',
           'target_period': '2015-06-01 to 2015-08-31',
           'source': 'cmems_obs-sst_bal_phy-temp_my_l4_P1D-m (analysed_sst)',
           'method': 'threshold = 90th percentile (Hazen/type-5) of +/-5-day day-of-year pools, 1992-2002 baseline, day 60 filled from days 59/61, 31-day circular moving mean; hot if SST >= threshold; MHW if >=5 consecutive hot days; 1-2 day gaps joined'})
enc = {'mhw': {'dtype': 'uint8', '_FillValue': None},
       'time': {'units': 'days since 1950-01-01 00:00:00', 'dtype': 'int32'},
       'latitude': {'dtype': 'float32'}, 'longitude': {'dtype': 'float32'}}
p_nc = os.path.join(out_dir, 'mhw_mask.nc')
dsm.to_netcdf(p_nc, engine='h5netcdf', encoding=enc)
print('wrote', p_nc, os.path.getsize(p_nc), 'bytes')

report = {
    "region": {"lat_min": 56.13, "lat_max": 57.33, "lon_min": 17.71, "lon_max": 18.91},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": "2015-06-01", "end": "2015-08-31"},
    "events": [{"onset": "2015-07-01", "end": "2015-07-08"}],
    "complete": True,
    "caveats": ("Baseline years are 1992-2002; per the prescribed method the +/-5 calendar-day day-of-year "
                "windows additionally draw on 1991-12-27..1991-12-31 and 2003-01-01..2003-01-05. "
                "The requested inclusive bounds fall between grid nodes: the analysed cells are the 60x60 grid "
                "cells with centres at latitude 56.14..57.32 N and longitude 17.72..18.90 E. Sea cells = 3300, "
                "all-NaN (land) cells = 300. Per-cell MHWs were searched only within 2015-06-01..2015-08-31, so "
                "an MHW straddling a window edge would be truncated (not the case here: the single regional event "
                "2015-07-01..2015-07-08 lies inside the window). Per-cell MHWs: 1073; no 1-2-day gap joins were "
                "required. All computations in float64; quantile is Hyndman-Fan type 5 (MATLAB default / numpy "
                "method='hazen').")
}
p_js = os.path.join(out_dir, 'report.json')
with open(p_js, 'w') as f:
    json.dump(report, f, indent=2)
print('wrote', p_js)

# verify both files by re-reading
v = xr.open_dataset(p_nc, engine='h5netcdf')
print('nc dims:', dict(v.sizes))
print('nc vars:', {k: (str(v[k].dtype), v[k].dims) for k in v.variables})
print('mhw dtype:', v['mhw'].dtype, 'sum:', int(v['mhw'].values.sum()),
      'unique:', np.unique(v['mhw'].values))
print('time:', str(v['time'].values[0])[:10], '..', str(v['time'].values[-1])[:10])
print('land cells all zero:', bool((v['mhw'].values[:, ~np.isfinite(
      xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')['analysed_sst'].isel(
          time=slice(glo,ghi+1), latitude=slice(132,192), longitude=slice(436,496)).values
      ).all(axis=0)] == 0).all()))
with open(p_js) as f:
    print('report.json:', json.dumps(json.load(f), indent=1)[:1200])
