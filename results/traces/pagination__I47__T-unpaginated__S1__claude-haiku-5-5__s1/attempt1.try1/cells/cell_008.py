def load_sub(day):
    p=d+f"sst_{day:%Y%m%d}.nc"
    with fs.open(p,'rb') as f:
        ds=xr.open_dataset(f,engine='h5netcdf')
        a=ds.analysed_sst.isel(time=0,latitude=slice(la[0],la[-1]+1),longitude=slice(lo[0],lo[-1]+1)).values.astype(np.float64)
    return a
t=time.time()
with ThreadPoolExecutor(16) as ex:
    arrs=list(ex.map(load_sub,days))
print(time.time()-t, len(arrs))
A=np.stack(arrs)
np.savez('/tmp/sst_cache.npz',A=A,days=np.array([str(x.date()) for x in days]),lat=lat[la],lon=lon[lo])
print(A.shape, np.isnan(A).mean())
