import numpy as np,pandas as pd,json,os,xarray as xr
S=np.load('/work/sst.npy');t=pd.DatetimeIndex(np.load('/work/t.npy'));lat=np.load('/work/lat.npy');lon=np.load('/work/lon.npy')
def doy(ix):
    m=ix.month.values;d=ix.day.values
    cum=np.array([0,31,60,91,121,152,182,213,244,274,305,335])
    return cum[m-1]+d
dy=doy(t)
tm=(t>='2013-06-01')&(t<='2013-08-31');Tt=t[tm];Ts=S[tm]
sea=np.isfinite(Ts).all(axis=0);print(sea.sum(),len(Tt))
base=np.where((t>='1992-01-01')&(t<='2002-12-31'))[0]
thr=np.full((367,)+S.shape[1:],np.nan);clim=thr.copy()
for d in range(1,367):
    if d==60:continue
    idx=[]
    for b in base:
        if dy[b]==d: idx+=list(range(b-5,b+6))
    P=S[idx][:,sea]
    thr[d][sea]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim[d][sea]=np.nanmean(P,axis=0)
def fin(a):
    a=a[1:].copy();a[59]=(a[58]+a[60])/2
    k=np.arange(366);o=np.zeros_like(a)
    for s in range(-15,16):o+=a[(k+s)%366]
    return o/31
thr=fin(thr);clim=fin(clim)
H=(Ts>=thr[doy(Tt)-1])&sea
nt=len(Tt);M=np.zeros(H.shape,bool)
for i in range(H.shape[1]):
  for j in range(H.shape[2]):
    if not sea[i,j]:continue
    h=H[:,i,j];runs=[];k=0
    while k<nt:
        if h[k]:
            e=k
            while e+1<nt and h[e+1]:e+=1
            if e-k+1>=5:runs.append([k,e])
            k=e+1
        else:k+=1
    mer=[]
    for r in runs:
        if mer and r[0]-mer[-1][1]-1<=2:mer[-1][1]=r[1]
        else:mer.append(r)
    for a,b in mer:M[a:b+1,i,j]=True
act=M.any(axis=(1,2));ev=[];k=0
while k<nt:
    if act[k]:
        e=k
        while e+1<nt and act[e+1]:e+=1
        ev.append({"onset":str(Tt[k].date()),"end":str(Tt[e].date())});k=e+1
    else:k+=1
print(ev,M.sum(),np.isnan(thr[:, sea]).sum())
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),M.astype('uint8'))},coords={'time':Tt.values,'lat':lat,'lon':lon}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":64.39,"lat_max":65.59,"lon_min":23.41,"lon_max":24.61},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2013-06-01","end":"2013-08-31"},"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))
print(os.path.abspath('output'))