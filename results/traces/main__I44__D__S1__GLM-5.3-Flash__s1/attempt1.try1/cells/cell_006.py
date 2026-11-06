import h5py, numpy as np, datetime as dt, time, pickle
from concurrent.fsspec_helper import *  if False else None
from concurrent.futures import ThreadPoolExecutor

LDIR='/work/nc'
EPOCH=dt.date(1981,1,1)
def daterange(a,b):
    d=a
    while d<=b:
        yield d
        d+=dt.timedelta(days=1)

all_dates=[d for d in daterange(dt.date(1991,12,27), dt.date(2004,8,31))]
N=len(all_dates)

def read_one(d):
    lp=f"{LDIR}/{d.strftime('sst_%Y%m%d.nc')}"
    with h5py.File(lp,'r') as f:
        t=f['time'][:]
        assert f['analysed_sst'].shape==(1,626,1051), f['analysed_sst'].shape
        sub=f['analysed_sst'][0, 491:551, 616:676].astype(np.float64)
        assert len(t)==1
        td=EPOCH+dt.timedelta(seconds=int(t[0]))
    return d, td, sub

t0=time.time()
data=np.full((N,60,60), np.nan, dtype=np.float64)
bad=[]
with ThreadPoolExecutor(max_workers=10) as exx:
    for d, td, sub in exx.map(read_one, all_dates):
        idx=(d-all_dates[0]).days
        if td!=d:
            bad.append((str(d),str(td)))
        data[idx]=sub
el=time.time()-t0
print('read seconds:', el)
print('date mismatches:', bad[:10], len(bad))
print('data shape', data.shape, data.dtype)
print('NaN fraction overall:', np.isnan(data).mean())
print('mem GB:', data.nbytes/1e9)

# quick look: land mask pattern
sea_any = np.isfinite(data).any(axis=0)
print('cells finite at least once:', sea_any.sum(), 'of', 60*60)
np.save('/work/data_region.npy', data)
with open('/work/all_dates.pkl','wb') as fh:
    pickle.dump(all_dates, fh)
print('saved.')
