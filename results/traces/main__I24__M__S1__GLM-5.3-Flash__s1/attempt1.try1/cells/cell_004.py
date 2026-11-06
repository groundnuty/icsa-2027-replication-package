import xarray as xr, numpy as np, os, datetime as dt
D='/data/icsa2027_data_20261101T090944Z/s1z'
def sel_days(a,b):
    d0=dt.date(*a); d1=dt.date(*b)
    return [d0+dt.timedelta(days=i) for i in range((d1-d0).days+1)]
days=sel_days((2004,6,1),(2004,8,31))
import time as _t
t0=_t.time()
stack=[]
for day in days:
    p=os.path.join(D,f"sst_{day:%Y%m%d}.nc")
    with xr.open_dataset(p,engine='h5netcdf') as ds:
        sub=ds['analysed_sst'].sel(latitude=slice(57.57,58.77),longitude=slice(10.25,11.45)).values[0]
        lat=ds['latitude'].sel(latitude=slice(57.57,58.77)).values
        lon=ds['longitude'].sel(longitude=slice(10.25,11.45)).values
    stack.append(sub.astype(np.float64))
A=np.stack(stack)
print('shape',A.shape,'load time %.1fs'%(_t.time()-t0))
print('lat',lat[0],lat[-1],len(lat))
print('lon',lon[0],lon[-1],len(lon))
np.save('/tmp/A_target.npy',A)
np.save('/tmp/lat.npy',lat); np.save('/tmp/lon.npy',lon)
sea=np.isfinite(A).all(axis=0)
print('sea cells:',sea.sum(),'total cells:',A[0].size)
print('nan pattern: any day with some nan in a sea cell?', (~np.isfinite(A[:,sea])).any())
# check some land values
print('land fraction per day:', (~np.isfinite(A)).mean(axis=(1,2))[:5])
