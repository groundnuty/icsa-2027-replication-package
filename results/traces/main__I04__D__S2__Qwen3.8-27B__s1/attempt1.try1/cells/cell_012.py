import os, json
import xarray as xr
p1 = '/work/output/mhw_mask.nc'; p2 = '/work/output/report.json'
print(p1, os.path.getsize(p1), 'bytes')
print(p2, os.path.getsize(p2), 'bytes')
ds = xr.open_dataset(p1, engine='h5netcdf')
v = ds['mhw']
print('dims:', v.dims, 'shape:', v.shape, 'dtype:', v.dtype, 'values in {0,1}:', set(np.unique(v.values).tolist()) if (np:=__import__('numpy')) else None)
print('n unique lat/lon:', ds.latitude.size, ds.longitude.size, 'time:', ds.time.size)
print('attrs of mhw:', dict(v.attrs))
rep = json.load(open(p2))
print(json.dumps(rep, indent=1))
assert v.dtype == np.uint8 and v.shape == (92, 60, 60)
assert set(rep) == {'region','baseline_analysed','target_analysed','events','complete','caveats'}
assert rep['complete'] is True and isinstance(rep['caveats'], str)
print('FINAL CHECKS PASSED')
