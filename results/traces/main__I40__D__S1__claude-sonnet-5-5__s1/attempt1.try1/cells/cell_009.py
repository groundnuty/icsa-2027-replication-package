import pickle,json,os
import numpy as np, pandas as pd, xarray as xr
dates,res=pickle.load(open('/work/res.pkl','rb'))
lat=res[0][1];lon=res[0][2]
D=pd.DatetimeIndex(dates)
A=np.stack([r[0] for r in res]).astype('float64')
dy=np.array([pd.Timestamp(2000,m,dd).day_of_year for m,dd in zip(D.month,D.day)])
ti=np.where((D>='2009-06-01'))[0]
base_c=np.where((D>='1992-01-01')&(D<='2002-12-31'))[0]
thr=np.full((366,60,60),np.nan)
for d in range(1,367):
    if d==60: continue
    idx=set()
    for c in base_c[dy[base_c]==d]: idx.update(range(c-5,c+6))
    thr[d-1]=np.nanquantile(A[sorted(idx)],0.9,axis=0,method='hazen')
thr[59]=(thr[58]+thr[60])/2
thr=sum(np.roll(thr,k,axis=0) for k in range(-15,16))/31
T=A[ti]; Td=dy[ti]
sea=np.isfinite(T).all(0)
hot=(T>=thr[Td-1])&sea
nt=len(ti);mhw=np.zeros_like(hot)
def runs(b):
    out=[];i=0
    while i<len(b):
        if b[i]:
            j=i
            while j<len(b) and b[j]: j+=1
            out.append((i,j));i=j
        else:i+=1
    return out
for y in range(60):
    for x in range(60):
        if not sea[y,x]: continue
        r=[q for q in runs(hot[:,y,x]) if q[1]-q[0]>=5]
        m=np.zeros(nt,bool)
        for k,(a,b) in enumerate(r):
            m[a:b]=True
            if k+1<len(r) and r[k+1][0]-b<=2: m[b:r[k+1][0]]=True
        mhw[:,y,x]=m
act=mhw.any((1,2))
ev=[(str(D[ti][a].date()),str(D[ti][b-1].date())) for a,b in runs(act)]
print(ev)
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),mhw.astype('uint8'))},coords={'time':D[ti],'lat':lat,'lon':lon}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":61.57,"lat_max":62.77,"lon_min":20.17,"lon_max":21.37},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2009-06-01","end":"2009-08-31"},"events":[{"onset":a,"end":b} for a,b in ev],"complete":True,"caveats":""},open('output/report.json','w'))