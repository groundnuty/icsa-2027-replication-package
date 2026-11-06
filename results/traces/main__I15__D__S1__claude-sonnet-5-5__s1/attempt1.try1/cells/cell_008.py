import numpy as np,pandas as pd,json,os,xarray as xr
lat=np.load('/work/lat.npy').astype('float64');lon=np.load('/work/lon.npy').astype('float64')
li=np.where((lat>=56.13-1e-4)&(lat<=57.33+1e-4))[0];lo=np.where((lon>=17.71-1e-4)&(lon<=18.91+1e-4))[0]
print(lat[li][[0,-1]],lon[lo][[0,-1]],len(li),len(lo))
def load(dr): return np.stack([np.load('/work/d/%s.npy'%t.strftime('%Y%m%d'))[np.ix_(li,lo)] for t in dr])
tgt=pd.date_range('2019-06-01','2019-08-31');T=load(tgt)
sea=np.isfinite(T).all(0);print(sea.sum())
bd=pd.date_range('1991-12-27','2003-01-05');B=load(bd)[:,sea]  # (t,cells)
def doy(d): 
    r=d.dayofyear.values.copy(); leap=d.is_leap_year; r=np.where(leap|(d.month<=2),r,r+1); return r
bdoy=doy(bd)
pos=np.arange(len(bd))
# baseline day indexes
isb=(bd>='1992-01-01')&(bd<='2002-12-31')
thr=np.full((366,B.shape[1]),np.nan);clim=thr.copy()
for d in range(1,367):
    if d==60: continue
    c=pos[isb&(bdoy==d)]
    idx=np.unique((c[:,None]+np.arange(-5,6)).ravel())
    idx=idx[(idx>=0)&(idx<len(bd))]
    pool=B[idx]
    thr[d-1]=np.nanquantile(pool,0.9,axis=0,method='hazen');clim[d-1]=np.nanmean(pool,0)
for a in (thr,clim): a[59]=(a[58]+a[60])/2
def sm(a): return np.mean([np.roll(a,-k,axis=0) for k in range(-15,16)],axis=0)
thr=sm(thr)
tdoy=doy(tgt)
hot=T[:,sea]>=thr[tdoy-1]
def runs(h):
    n,m=h.shape;out=np.zeros_like(h)
    for j in range(m):
        x=h[:,j];i=0;segs=[]
        while i<n:
            if x[i]:
                k=i
                while k<n and x[k]:k+=1
                if k-i>=5:segs.append([i,k])
                i=k
            else:i+=1
        mg=[]
        for s in segs:
            if mg and s[0]-mg[-1][1]<=2: mg[-1][1]=s[1]
            else: mg.append(s)
        for s,e in mg: out[s:e,j]=True
    return out
M=runs(hot)
full=np.zeros(T.shape,'uint8');full[:,sea]=M
act=full.any((1,2));ev=[];i=0
while i<len(act):
    if act[i]:
        k=i
        while k<len(act) and act[k]:k+=1
        ev.append({"onset":tgt[i].strftime('%Y-%m-%d'),"end":tgt[k-1].strftime('%Y-%m-%d')});i=k
    else:i+=1
print(ev,full.sum())
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),full)},coords={'time':tgt,'lat':lat[li].astype('float32'),'lon':lon[lo].astype('float32')}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":56.13,"lat_max":57.33,"lon_min":17.71,"lon_max":18.91},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2019-06-01","end":"2019-08-31"},"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))