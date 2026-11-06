import numpy as np, os, json, sys
print('numpy', np.__version__, 'python', sys.version.split()[0])
try:
    import xarray, h5netcdf
    print('xarray', xarray.__version__)
except Exception as e:
    print('xarray issue', e)
os.makedirs('/tmp/mhwtest', exist_ok=True)
with open('/tmp/mhwtest/marker.txt','w') as f:
    f.write('persist-test-42')
os.makedirs('output', exist_ok=True)
with open('output/persist_marker.txt','w') as f:
    f.write('cwd-persist-42')
print('markers written; cwd =', os.getcwd())
