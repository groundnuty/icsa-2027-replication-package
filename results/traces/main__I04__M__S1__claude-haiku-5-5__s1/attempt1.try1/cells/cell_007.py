import numpy as np, pandas as pd, json
z=np.load("/tmp/sst_sub.npz"); A=z["A"]; dts=pd.to_datetime(z["dates"])
# doy by month/day, leap-year convention
ref=pd.date_range("2000-01-01","2000-12-31")
doy_of_md={(d.month,d.day):i+1 for i,d in enumerate(ref)}
doy_all=np.array([doy_of_md[(d.month,d.day)] for d in dts])
# baseline dates
bstart,bend=pd.Timestamp("1992-01-01"),pd.Timestamp("2002-12-31")
ext_start,ext_end=pd.Timestamp("1991-12-27"),pd.Timestamp("2003-01-05")
idx_of={d:i for i,d in enumerate(dts)}
ny,nx=A.shape[1:]
thr=np.full((367,ny,nx),np.nan); clim=np.full((367,ny,nx),np.nan)
base_dates=pd.date_range(bstart,bend)
for d in range(1,367):
    if d==60: continue
    bs=[b for b in base_dates if doy_of_md[(b.month,b.day)]==d]
    xs=set()
    for b in bs:
        for k in range(-5,6):
            x=b+pd.Timedelta(days=k)
            if ext_start<=x<=ext_end: xs.add(x)
    ii=[idx_of[x] for x in sorted(xs)]
    P=A[ii]  # pool, shape n,ny,nx
    with np.errstate(all='ignore'):
        thr[d]=np.nanquantile(P,0.9,axis=0,method="hazen")
        clim[d]=np.nanmean(P,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(arr):  # arr indexed 1..366 at [1..366]
    v=arr[1:367]  # 366,...
    out=np.empty_like(v)
    for i in range(366):
        ids=[(i+k)%366 for k in range(-15,16)]
        out[i]=np.mean(v[ids],axis=0)
    return out
T=smooth(thr); C=smooth(clim)  # index i -> doy i+1
print(np.isnan(T).sum(), np.isnan(C).sum(), T[150,0,0], C[150,0,0])