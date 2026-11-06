import fsspec
import xarray as xr
import numpy as np
fs = fsspec.filesystem('onedata')
root = 'icsa2027_data_20261101T090944Z/s1z'
with fs.open(root+'/sst_20090601.nc','rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
lat = ds.latitude.values
lon = ds.longitude.values
print('lat dtype', lat.dtype, 'first/last', repr(lat[0]), repr(lat[-1]), 'len', len(lat))
print('lon dtype', lon.dtype, 'first/last', repr(lon[0]), repr(lon[-1]), 'len', len(lon))
# check spacing
dlat = np.diff(lat[:20])
dLon = np.diff(lon[:20])
print('dlat sample', [repr(x) for x in dlat[:5]], 'min', dlat.min(), 'max', dlat.max())
# region slice
sel_lat = lat[(lat>=56.09-1e-6)&(lat<=57.29+1e-6)]
sel_lon = lon[(lon>=10.55-1e-6)&(lon<=11.75+1e-6)]
print('n lat in region:', len(sel_lat), 'n lon in region:', len(sel_lon))
print('lat values:', [repr(x) for x in sel_lat[:6]], '...', [repr(x) for x in sel_lat[-4:]])
print('lon values:', [repr(x) for x in sel_lon[:6]], '...', [repr(x) for x in sel_lon[-4:]])
print('analysed_sst units attr:', ds.analysed_sst.attrs)