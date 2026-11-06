import xarray as xr, numpy as np
ds = xr.open_dataset('/work/test/sst_20170601.nc', engine='h5netcdf')
lat = ds['latitude'].values
lon = ds['longitude'].values
print('lat[0:5]', lat[:5], 'lat[-3:]', lat[-3:])
print('lon[0:5]', lon[0:5], 'lon[-3:]', lon[-3:])
print('lat dtype', lat.dtype, 'diff uniq', np.unique(np.diff(lat.astype('float64'))))
print('lon dtype', lon.dtype, 'diff uniq', np.unique(np.diff(lon.astype('float64'))))
# find points near region bounds
latd = lat.astype('float64'); lond = lon.astype('float64')
print('lat near 62.25:', latd[(latd>62.20)&(latd<62.30)])
print('lat near 63.45:', latd[(latd>63.40)&(latd<63.50)])
print('lon near 18.73:', lond[(lond>18.68)&(lond<18.78)])
print('lon near 19.93:', lond[(lond>19.88)&(lond<19.98)])
import numpy, h5py, scipy
print('numpy', numpy.__version__, 'h5py', h5py.__version__, 'scipy', scipy.__version__)
# test quantile method availability
print(np.quantile(np.arange(10.), 0.9, method='hazen'))
# check region selection counts with closed bounds
latm = (latd >= 62.25 - 1e-9) & (latd <= 63.45 + 1e-9)
lonm = (lond >= 18.73 - 1e-9) & (lond <= 19.93 + 1e-9)
print('n lat cells', latm.sum(), latd[latm][[0,-1]])
print('n lon cells', lonm.sum(), lond[lonm][[0,-1]])
