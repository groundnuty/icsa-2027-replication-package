import fsspec,pandas as pd,numpy as np,xarray as xr,os
from concurrent.futures import ThreadPoolExecutor
def get(d):
    fs=fsspec.filesystem('onedata')
    f=f'icsa2027_data_20261101T090944Z/s1z/sst_{d:%Y%m%d}.nc'
    err=None
    for t in range(4):
        try:
            with fs.open(f,'rb') as fh:
                return xr.open_dataset(fh,engine='h5netcdf').load()
        except FileNotFoundError: return None
        except Exception as e: err=e
    return ('err',str(err))
r0=get(pd.Timestamp('2003-06-01'))
la=r0.latitude.values;lo=r0.longitude.values
li=np.where((la>=60.49-1e-4)&(la<=61.69+1e-4))[0];oi=np.where((lo>=17.25-1e-4)&(lo<=18.45+1e-4))[0]
dates=pd.date_range('1991-12-27','2003-08-31')
def sub(d):
    x=get(d)
    if x is None or isinstance(x,tuple): return x
    return x.analysed_sst.values[0][np.ix_(li,oi)]
with ThreadPoolExecutor(16) as ex: res=list(ex.map(sub,dates))
miss=[d for d,r in zip(dates,res) if r is None];errs=[(d,r) for d,r in zip(dates,res) if isinstance(r,tuple)]
print(len(miss),len(errs),miss[:5],errs[:3])
ok=[r for r in res if isinstance(r,np.ndarray)]
np.save('output/sst.npy',np.array([r if isinstance(r,np.ndarray) else np.full((len(li),len(oi)),np.nan,'f4') for r in res]))
np.save('output/ll.npy',np.array([la[li],lo[oi]],dtype=object),allow_pickle=True)
print(np.nanmin(ok[0]),np.nanmax(ok[0]),np.isnan(ok[0]).sum(), r0.analysed_sst.attrs, r0.time.values)