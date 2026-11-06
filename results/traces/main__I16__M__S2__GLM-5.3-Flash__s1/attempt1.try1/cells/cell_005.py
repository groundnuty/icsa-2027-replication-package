import numpy as np, xarray as xr, warnings
warnings.filterwarnings('ignore')
path='/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds=xr.open_dataset(path, engine='h5netcdf')
td=ds['time'].values.astype('datetime64[D]')
ilat0, ilat1, ilon0, ilon1 = np.load('/tmp/idx.npy')
la=slice(int(ilat0), int(ilat1)+1); lo=slice(int(ilon0), int(ilon1)+1)
B=np.load('/tmp/B.npy')
sst=ds['analysed_sst']
d0=np.datetime64('1991-12-27')
for date in ['1992-06-01','1996-02-29','2000-12-31','2003-01-05','1991-12-27']:
    k=int((np.datetime64(date)-d0).astype(int))
    chk=B[k].astype('float64')
    direct=np.asarray(sst.isel(time=int(np.flatnonzero(td==np.datetime64(date))[0]), latitude=la, longitude=lo).values, 'float64')
    both_nan=np.isnan(chk)&np.isnan(direct)
    same=np.where(both_nan, True, chk==direct)
    print(date, "identical:", bool(same.all()), "| nnan:", int(np.isnan(chk).sum()))
# global stats over baseline-ext block
fin=np.isfinite(B)
print("overall finite frac: %.6f" % fin.mean())
percell_all = fin.all(axis=0)
print("cells finite on ALL 4028 baseline-ext days:", int(percell_all.sum()))
# also load target days
t_idx=np.load('/tmp/t_idx.npy')
T=np.empty((t_idx.size,60,60),'float32')
T = sst.isel(time=slice(int(t_idx[0]), int(t_idx[-1])+1), latitude=la, longitude=lo).values
T=np.asarray(T, 'float32')
np.save('/tmp/T.npy', T)
finT=np.isfinite(T)
print("target finite frac: %.6f | cells finite ALL 92 target days:", round(float(finT.mean()),6), int(finT.all(axis=0).sum()))
np.save('/tmp/sea_all.npy', fin.all(axis=0) & finT.all(axis=0))
print("sea cells (finite all 4028 ext-baseline days AND all 92 target days):", int((fin.all(axis=0)&finT.all(axis=0)).sum()))
