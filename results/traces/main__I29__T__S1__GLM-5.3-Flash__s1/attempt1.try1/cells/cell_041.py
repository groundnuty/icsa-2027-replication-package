import fsspec, h5py, numpy as np, datetime
# read the dataset's own lat/lon arrays exactly
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s1z/sst_20150601.nc','rb')
with h5py.File(f,'r') as h:
    lat = h['latitude'][218:278].astype(np.float64)
    lon = h['longitude'][601:661].astype(np.float64)
f.close()
print('lat[0], lat[-1]:', repr(lat[0]), repr(lat[-1]))
print('lon[0], lon[-1]:', repr(lon[0]), repr(lon[-1]))
# strictly check bounds in float64
print('lat within [57.85, 59.05]:', bool((lat>=57.85).all() and (lat<=59.05).all()))
print('lon within [21.01, 22.21]:', bool((lon>=21.01).all() and (lon<=22.21).all()))
np.save('latvals_ds.npy', lat.astype(np.float32)); np.save('lonvals_ds.npy', lon.astype(np.float32))
print('saved exact coord values')
