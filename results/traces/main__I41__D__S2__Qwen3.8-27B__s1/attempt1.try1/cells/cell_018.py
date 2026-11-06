path = '/work/pipeline.py'
src = open(path).read()
old = """out = xr.Dataset(
    data_vars={'mhw': (('time', 'latitude', 'longitude'), mask, {})},
    coords={
        'time': ('time', times[t0t:t1t + 1]),
        'latitude': ('latitude', lat[latm]),
        'longitude': ('longitude', lon[lonm]),
    },
)
out.to_netcdf('/work/output/mhw_mask.nc')
print("wrote mhw_mask.nc", out.sizes, out['mhw'].dtype)"""
new = """m3 = mask.reshape(92, len(latm), len(lonm))
out = xr.Dataset(
    data_vars={'mhw': (('time', 'lat', 'lon'), m3, {'long_name': 'per-cell marine heatwave mask (1 = in MHW, 0 otherwise)'})},
    coords={
        'time': ('time', times[t0t:t1t + 1]),
        'lat': ('lat', lat[latm]),
        'lon': ('lon', lon[lonm]),
    },
)
out.to_netcdf('/work/output/mhw_mask.nc')
print("wrote mhw_mask.nc", dict(out.sizes), out['mhw'].dtype)"""
assert old in src
src = src.replace(old, new)
open(path, 'w').write(src)
print("patched output section")
