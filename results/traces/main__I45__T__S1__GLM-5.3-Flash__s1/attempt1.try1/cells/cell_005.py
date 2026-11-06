import fsspec, h5py, numpy as np, time
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z'

# existence checks for key dates
for d in ['19911227','19911231','19920101','20021231','20030105','20090601','20090831','20090815']:
    print(d, fs.exists(f'{base}/sst_{d}.nc'))

lat_lo, lat_hi, lon_lo, lon_hi = 63.31, 64.51, 21.31, 22.51

t0=time.time()
with fs.open(f'{base}/sst_20090615.nc','rb') as f:
    with h5py.File(f,'r') as hf:
        dset = hf['analysed_sst']
        print('chunks', dset.chunks, 'shape', dset.shape, 'dtype', dset.dtype, 'compression', dset.compression)
        lat = hf['latitude'][:]
        lon = hf['longitude'][:]
        tval = hf['time'][:]
        print('time raw', tval, hf['time'].attrs)
        lat64 = np.asarray(lat, dtype='float64'); lon64 = np.asarray(lon, dtype='float64')
        latm = (lat64 >= lat_lo) & (lat64 <= lat_hi)
        lonm = (lon64 >= lon_lo) & (lon64 <= lon_hi)
        i0,i1 = np.where(latm)[0][[0,-1]]; j0,j1 = np.where(lonm)[0][[0,-1]]
        print('lat idx', i0, i1, lat[i0], lat[i1], 'n', i1-i0+1)
        print('lon idx', j0, j1, lon[j0], lon[j1], 'n', j1-j0+1)
        t1=time.time()
        sub = dset[0, i0:i1+1, j0:j1+1]
        print('read subset s:', time.time()-t1, sub.shape, sub.dtype)
        print('finite frac', np.isfinite(sub).mean(), 'min/max', np.nanmin(sub), np.nanmax(sub))
print('total s:', time.time()-t0)
