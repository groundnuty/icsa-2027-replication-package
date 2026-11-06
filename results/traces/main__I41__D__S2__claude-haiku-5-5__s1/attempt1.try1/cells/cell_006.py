
import xarray as xr, numpy as np, pandas as pd, json, os
os.makedirs('/work/output', exist_ok=True)
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
ilat=np.where((lat>=61.57-1e-6)&(lat<=62.77+1e-6))[0]
ilon=np.where((lon>=20.17-1e-6)&(lon<=21.37+1e-6))[0]
# time index: extended baseline range + target
ext_start=pd.Timestamp('1991-12-27'); ext_end=pd.Timestamp('2003-01-05')
tgt_start=pd.Timestamp('2021-06-01'); tgt_end=pd.Timestamp('2021-08-31')
times=pd.DatetimeIndex(ds.time.values)
sel=np.where(((times>=ext_start)&(times<=ext_end))|((times>=tgt_start)&(times<=tgt_end)))[0]
sub=ds.analysed_sst.isel(time=sel, latitude=ilat, longitude=ilon).load()
T=pd.DatetimeIndex(sub.time.values)
A=sub.values.astype(np.float64)  # (time, lat, lon)
print(A.shape, T[0], T[-1])

# day-of-year table (leap calendar)
def doy_of(ts):
    return ts.map(lambda t: pd.Timestamp(2000,t.month,t.day).dayofyear)  # 2000 leap: Feb29=60, Dec31=366
doy_all=np.array(doy_of(T))
base_mask=(T>=pd.Timestamp('1992-01-01'))&(T<=pd.Timestamp('2002-12-31'))
base_dates=T[base_mask]; base_doy=doy_all[base_mask]
Ab=A[base_mask]  # not used directly; pool uses extended
# pools
ext_idx=np.where((T>=ext_start)&(T<=ext_end))[0]
Text=T[ext_idx]
Aext=A[ext_idx]
nlat,nlon=len(ilat),len(ilon)
thr=np.full((367,nlat,nlon),np.nan); clim=np.full((367,nlat,nlon),np.nan)
for d in range(1,367):
    if d==60: continue
    bd=base_dates[base_doy==d]
    if len(bd)==0: continue
    inpool=np.zeros(len(Text),bool)
    for b in bd:
        inpool |= (np.abs((Text-b).days)<=5)
    P=Aext[inpool]
    thr[d]=np.nanpercentile(P,90,axis=0,method='hazen')
    clim[d]=np.nanmean(P,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(x):
    y=np.empty_like(x)
    idx=np.arange(1,367)
    for i,d in enumerate(idx):
        ds_=[((d-1+k)%366) for k in range(-15,16)]
        y[d]=np.mean(x[1:][ds_],axis=0)  # x[1:] indexes doy 1..366 as 0..365
    return y
thr_s=smooth(thr[1:].reshape(366,-1).reshape(366,nlat,nlon)) if False else None
# simpler smoothing on arrays of shape (366,...)
def smooth366(X):  # X shape (366,...) indexed doy-1
    out=np.empty_like(X)
    for i in range(366):
        ids=[(i+k)%366 for k in range(-15,16)]
        out[i]=X[ids].mean(axis=0)
    return out
thr_s=smooth366(thr[1:]); clim_s=smooth366(clim[1:])
print(np.isnan(thr_s).sum(), np.isnan(clim_s).sum(), np.nanmean(thr_s))
