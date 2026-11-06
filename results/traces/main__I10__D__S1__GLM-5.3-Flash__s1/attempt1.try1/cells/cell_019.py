import xarray as xr, numpy as np, json
ds = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
print(ds)
print('mhw dtype:', ds['mhw'].dtype, '| dims:', ds['mhw'].dims, '| shape:', ds['mhw'].shape)
m = ds['mhw'].values
print('unique values:', np.unique(m), '| ones:', int(m.sum()))
print('time[0]:', str(ds.time.values[0])[:10], '| time[-1]:', str(ds.time.values[-1])[:10], '| ntime:', ds.time.size)
print('lat:', float(ds.lat[0]), '->', float(ds.lat[-1]), '| lon:', float(ds.lon[0]), '->', float(ds.lon[-1]))
print('contiguous time:', bool(np.all(np.diff(ds.time.values)==np.timedelta64(1,'D'))))
with open('/work/output/report.json') as f:
    rep = json.load(f)
print(json.dumps(rep, indent=1))
assert set(rep.keys())=={'region','baseline_analysed','target_analysed','events','complete','caveats'}
assert ds['mhw'].dtype==np.uint8
assert ds['mhw'].dims==('time','lat','lon')
# mask consistency: days with no active cells should be all zero
active = m.any(axis=(1,2))
zero_days = np.flatnonzero(~active)
print('all-zero days:', zero_days.size, '| mhw ones == sum over active days:', int(m[active].sum())==int(m.sum()))
print('VALIDATION OK')
