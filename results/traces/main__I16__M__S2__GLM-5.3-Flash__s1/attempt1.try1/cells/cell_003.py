import numpy as np, xarray as xr, warnings, time, os
warnings.filterwarnings('ignore')
print("tmp persisted:", os.path.exists('/tmp/latlon.npy'), "| cwd:", os.getcwd())
path='/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds=xr.open_dataset(path, engine='h5netcdf')
td = ds['time'].values.astype('datetime64[D]')
lat=ds['latitude'].values; lon=ds['longitude'].values
ilat=np.flatnonzero((lat.astype('float64')>=56.63-1e-6)&(lat.astype('float64')<=57.83+1e-6))
ilon=np.flatnonzero((lon.astype('float64')>=20.23-1e-6)&(lon.astype('float64')<=21.43+1e-6))
np.save('/tmp/idx.npy', np.array([ilat[0], ilat[-1], ilon[0], ilon[-1]]))
np.save('/tmp/lat_reg.npy', lat[ilat]); np.save('/tmp/lon_reg.npy', lon[ilon])
b_idx=np.flatnonzero((td>=np.datetime64('1991-12-27'))&(td<=np.datetime64('2003-01-05')))
t_idx=np.flatnonzero((td>=np.datetime64('2008-06-01'))&(td<=np.datetime64('2008-08-31')))
np.save('/tmp/b_idx.npy', b_idx); np.save('/tmp/t_idx.npy', t_idx)
assert np.all(np.diff(td.astype(np.int64))==1), "time not contiguous daily"
assert np.all(np.diff(b_idx)==1) and np.all(np.diff(t_idx)==1)
print("b_idx:", b_idx[0], b_idx[-1], b_idx.size, "| t_idx:", t_idx[0], t_idx[-1], t_idx.size)
sst=ds['analysed_sst']
la=slice(int(ilat[0]), int(ilat[-1])+1); lo=slice(int(ilon[0]), int(ilon[-1])+1)
half=(b_idx.size+1)//2
part=b_idx[:half]
out=np.empty((part.size, ilat.size, ilon.size), 'float32')
t00=time.time(); step=366
for s in range(0, part.size, step):
    e=min(s+step, part.size); t0=time.time()
    out[s:e]=sst.isel(time=slice(int(part[s]), int(part[e-1])+1), latitude=la, longitude=lo).values
    print("batch %4d-%4d  %.1fs" % (s, e-1, time.time()-t0), flush=True)
np.save('/tmp/sst_b1.npy', out)
print("part1 saved:", out.shape, "total %.1fs" % (time.time()-t00))
print("finite frac part1 day0: %.4f" % np.isfinite(out[0]).mean())
