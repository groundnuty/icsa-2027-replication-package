import h5py, numpy as np, os, datetime as dt, time
D='/data/icsa2027_data_20261101T090944Z/s1z'
lat_ref=None; lon_ref=None
i0,i1,j0,j1=204,264,63,123
need=[]
d0=dt.date(1991,12,27); d1=dt.date(2004,8,31)
n=(d1-d0).days+1
need=[d0+dt.timedelta(days=i) for i in range(n)]
A=np.full((len(need),60,60),np.nan,dtype=np.float64)
t0=time.time()
grid_ok=True
for k,day in enumerate(need):
    p=os.path.join(D,f"sst_{day:%Y%m%d}.nc")
    with h5py.File(p,'r') as f:
        lat=f['latitude'][i0:i1]; lon=f['longitude'][j0:j1]
        if lat_ref is None: lat_ref=lat; lon_ref=lon
        else:
            grid_ok &= np.array_equal(lat,lat_ref) and np.array_equal(lon,lon_ref)
        blk=f['analysed_sst'][0,i0:i1,j0:j1]
    A[k]=blk.astype(np.float64)
    if (k+1)%500==0: print(k+1,'%.1fs'%(time.time()-t0))
print('done %.1fs'%(time.time()-t0), 'grid_ok',grid_ok, A.shape)
np.save('/tmp/A_all.npy',A)
dates=np.array([d.toordinal() for d in need])
np.save('/tmp/dates_ord.npy',dates)
print('finite frac overall %.4f'%np.isfinite(A).mean())
# any all-nan days?
anynan_day = (~np.isfinite(A)).all(axis=(1,2)).sum()
print('days fully nan in region:',anynan_day)
