from concurrent.futures import ThreadPoolExecutor
ii=slice(li[0],li[-1]+1); jj=slice(lj[0],lj[-1]+1)
def load(x):
    p=f"{d}/sst_{x:%Y%m%d}.nc"
    with xr.open_dataset(p, engine='h5netcdf') as f:
        t=pd.Timestamp(f.time.values[0])
        a=f.analysed_sst.isel(time=0, latitude=ii, longitude=jj).values.astype(np.float64)
        assert f.latitude.values[li[0]]==lat[li[0]]
    return t,a
with ThreadPoolExecutor(16) as ex:
    res=list(ex.map(load, alld))
bad=[(x,t) for x,(t,a) in zip(alld,res) if t!=x]
print('time mismatches',len(bad), bad[:3])
A=np.stack([a for t,a in res]); print(A.shape, np.isnan(A).mean())