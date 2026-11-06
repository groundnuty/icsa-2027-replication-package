import fsspec
fs = fsspec.filesystem('onedata')
try:
    root = fs.ls('/')
except Exception as e:
    print('root ls error:', type(e).__name__, str(e)[:300])
    root = []
print('ROOT:', root)

probe = []
for r in root:
    b = r.rstrip('/')
    probe.append(b + '/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc')
probe.append('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc')
for p in probe:
    try:
        print('OK ', p, fs.info(p))
    except Exception as e:
        print('ERR', p, type(e).__name__, str(e)[:120])