
import xarray as xr,numpy as np,pandas as pd,json,os
from scipy.ndimage import label
b=xr.open_dataarray('/tmp/b.nc');t=xr.open_dataarray('/tmp/t.nc')
bt=pd.DatetimeIndex(b.time.values);B=b.values.astype('float64')
def doy(i): 
    return np.array([ (pd.Timestamp(2000,x.month,x.day).dayofyear) for x in i])
bd=doy(bt)
core=np.where((bt>='1992-01-01')&(bt<='2002-12-31'))[0]
ny,nx=B.shape[1:]
thr=np.full((366,ny,nx),np.nan);clim=thr.copy()
for d in range(1,367):
    if d==60: continue
    idx=set()
    for i in core[bd[core]==d]:
        idx.update(range(i-5,i+6))
    idx=sorted(j for j in idx if 0<=j<len(bt))
    # pool may count duplicates? use union of days (distinct)... 
    P=B[idx]
    thr[d-1]=np.nanquantile(P,0.9,axis=0,method='hazen');clim[d-1]=np.nanmean(P,axis=0)
