import numpy as np,pandas as pd,json,xarray as xr,os
dates=pd.date_range('1991-12-27','2003-01-05')
tg=pd.date_range('2012-06-01','2012-08-31')
def ld(d):
    z=np.load(f'/work/c/{d:%Y%m%d}.npz');return z['v'],z['la'],z['lo']
A=[ld(d) for d in dates]; la,lo=A[0][1],A[0][2]
print(la[[0,-1]],lo[[0,-1]],len(la),len(lo))
S=np.stack([a[0] for a in A]); T=np.stack([ld(d)[0] for d in tg])
S[S<-1e3]=np.nan  # fillvalue guard
print(np.nanmin(S),np.nanmax(S),np.isnan(T).sum())
sea=np.isfinite(T).all(0); print(sea.sum(),sea.size)
def doy(d): 
    m=np.array([d.month]);return int(pd.Timestamp(2000,d.month,d.day).dayofyear)  # leap-year mapping
dd=np.array([doy(d) for d in dates])
# window pool: for each baseline date with doy d (1992-01-01..2002-12-31), days within ±5 of it
inb=(dates>=pd.Timestamp('1992-01-01'))&(dates<=pd.Timestamp('2002-12-31'))
ny,nx=sea.shape
thr=np.full((366,ny,nx),np.nan);clim=thr.copy()
idx=np.arange(len(dates))
for d in range(1,367):
    if d==60: continue
    c=idx[inb&(dd==d)]
    sel=np.unique(np.concatenate([np.arange(i-5,i+6) for i in c]))
    sel=sel[(sel>=0)&(sel<len(dates))]
    P=S[sel]
    thr[d-1]=np.nanquantile(P,0.9,axis=0,method='hazen');clim[d-1]=np.nanmean(P,0)
for a in(thr,clim): a[59]=(a[58]+a[60])/2
def sm(a):
    return sum(np.roll(a,-k,axis=0) for k in range(-15,16))/31
thr=sm(thr)
td=np.array([doy(d) for d in tg])
hot=T>=thr[td-1]
hot&=sea
# per-cell
mhw=np.zeros_like(hot)
nt=len(tg)
for i in range(ny):
  for j in range(nx):
    if not sea[i,j]: continue
    h=hot[:,i,j];runs=[];k=0
    while k<nt:
        if h[k]:
            e=k
            while e+1<nt and h[e+1]:e+=1
            if e-k+1>=5: runs.append([k,e])
            k=e+1
        else:k+=1
    mer=[]
    for r in runs:
        if mer and r[0]-mer[-1][1]-1<=2: mer[-1][1]=r[1]
        else: mer.append(r[:])
    for a,b in mer: mhw[a:b+1,i,j]=True
act=mhw.any((1,2));ev=[];k=0
while k<nt:
    if act[k]:
        e=k
        while e+1<nt and act[e+1]:e+=1
        ev.append({"onset":f"{tg[k]:%Y-%m-%d}","end":f"{tg[e]:%Y-%m-%d}"});k=e+1
    else:k+=1
print(ev,mhw.sum())
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype('uint8'))},coords={'time':tg,'lat':la,'lon':lo}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":54.45,"lat_max":55.65,"lon_min":16.05,"lon_max":17.25},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2012-06-01","end":"2012-08-31"},"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))