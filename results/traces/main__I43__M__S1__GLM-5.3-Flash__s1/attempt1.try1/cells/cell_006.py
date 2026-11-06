import numpy as np, sys, os
print('python', sys.version)
print('numpy', np.__version__)
try:
    import h5py
    print('h5py', h5py.__version__)
except Exception as e:
    print('h5py missing', e)
try:
    import netCDF4
    print('netCDF4', netCDF4.__version__)
except Exception as e:
    print('netCDF4 missing', e)
try:
    import h5netcdf
    print('h5netcdf', h5netcdf.__version__)
except Exception as e:
    print('h5netcdf missing', e)
print('cwd', os.getcwd())
# writability test
os.makedirs('output', exist_ok=True)
with open('output/_test.txt','w') as f:
    f.write('ok')
print('write ok', os.path.exists('output/_test.txt'))
os.remove('output/_test.txt')
# hazen behaviour for small n
for n in [1,2,3,4,5,6]:
    x = np.arange(1, n+1, dtype=float)
    try:
        q = np.quantile(x, 0.9, method='hazen')
        print('n',n,'hazen p90 of 1..n:', q)
    except Exception as e:
        print('n',n,'error',e)
