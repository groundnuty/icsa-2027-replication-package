
import numpy as np, pandas as pd, json
z=np.load('/work/sub.npz'); A=z['A']; tim_d=pd.DatetimeIndex(z['tim'].view('datetime64[ns]'))
tgt_mask=(tim_d>=pd.Timestamp('2022-06-01'))&(tim_d<=pd.Timestamp('2022-08-31'))
Tt=A[tgt_mask]; tt_dates=tim_d[tgt_mask]
sea=np.all(np.isfinite(Tt),axis=0)
print("sea cells",sea.sum(),"target days",tgt_mask.sum(), "any NaN in target non-sea:", np.isnan(Tt[:,~sea]).any(axis=0).sum())
doy_all=np.array([pd.Timestamp(2000,x.month,x.day).dayofyear for x in tim_d])
doy_tgt=doy_all[tgt_mask]
base_mask=(tim_d>=pd.Timestamp('1992-01-01'))&(tim_d<=pd.Timestamp('2002-12-31'))
pos={x:i for i,x in enumerate(tim_d)}
pool_idx={d:[] for d in range(1,367) if d!=60}
for bi in np.where(base_mask)[0]:
    d=doy_all[bi]
    if d==60: continue
    B=tim_d[bi]
    for k in range(-5,6):
        D=B+pd.Timedelta(days=k)
        if D in pos: pool_idx[d].append(pos[D])
print([len(pool_idx[d]) for d in (1,59,61,100,366)])
thr=np.full((367,)+A.shape[1:],np.nan); clim=np.full_like(thr,np.nan)
for d in pool_idx:
    P=A[pool_idx[d]]
    thr[d]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim[d]=np.nanmean(P,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(x):  # x indexed 1..366 in x[1:]
    v=x[1:367]; out=np.empty_like(v)
    for i in range(366):
        ids=[(i+k)%366 for k in range(-15,16)]
        out[i]=np.mean(v[ids],axis=0)
    return out
thr_s=smooth(thr); clim_s=smooth(clim)  # index d-1
print(np.isnan(thr_s[:,sea]).sum(), np.isnan(clim_s[:,sea]).sum())
