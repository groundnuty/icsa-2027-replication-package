import numpy as np, xarray as xr, warnings, time
warnings.filterwarnings('ignore')
path='/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds=xr.open_dataset(path, engine='h5netcdf')
ilat0, ilat1, ilon0, ilon1 = np.load('/tmp/idx.npy')
b_idx=np.load('/tmp/b_idx.npy')
sst=ds['analysed_sst']
la=slice(int(ilat0), int(ilat1)+1); lo=slice(int(ilon0), int(ilon1)+1)
part=b_idx[2014:]
out=np.empty((part.size, 60, 60), 'float32')
t00=time.time(); step=366
for s in range(0, part.size, step):
    e=min(s+step, part.size); t0=time.time()
    out[s:e]=sst.isel(time=slice(int(part[s]), int(part[e-1])+1), latitude=la, longitude=lo).values
    print("batch %4d-%4d  %.1fs" % (s, e-1, time.time()-t0), flush=True)
np.save('/tmp/sst_b2.npy', out)
print("part2 saved:", out.shape, "total %.1fs" % (time.time()-t00))
print("finite frac part2 last day: %.4f" % np.isfinite(out[-1]).mean())
# quick sanity: reassemble and check a couple of dates against direct reads
b1=np.load('/tmp/sst_b1.npy'); B=np.concatenate([b1,out],axis=0)
td=ds['time'].values.astype('datetime64[D]')
d0=np.datetime64('1991-12-27')
chk1=B[(np.datetime64('1992-06-01')-d0).astype(int)]
chk2=B[(np.datetime64('2003-01-05')-d0).astype(int)]
d1=np.asarray(sst.isel(time=int(np.flatnonzero(td==np.datetime64('1992-06-01'))[0]), latitude=la, longitude=lo).values, 'float64')
d2=np.asarray(sst.isel(time=int(np.flatnonzero(td==np.datetime64('2003-01-05'))[0]), latitude=la, longitude=lo).values, 'float64')
print("match 1992-06-01:", np.array_equal(chk1.astype('float64'), d1), "| match 2003-01-05:", np.array_equal(chk2.astype('float64'), d2))
np.save('/tmp/B.npy', B)
print("B shape:", B.shape, "dtype:", B.dtype)
