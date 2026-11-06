tt=pd.DatetimeIndex(t[b0:b1])
doy=np.array([ (m-1)*0 for m in tt.month])
cum=np.cumsum([0,31,29,31,30,31,30,31,31,30,31,30])
doy=cum[tt.month-1]+tt.day
inb=(tt>="1992-01-01")&(tt<="2002-12-31")
ny,nx=60,60
thr=np.full((366,ny,nx),np.nan);clm=thr.copy()
for dd in range(1,367):
    if dd==60: continue
    c=np.where(inb&(doy==dd))[0]
    idx=np.unique(np.concatenate([np.arange(k-5,k+6) for k in c]))
    pool=base[idx]
    thr[dd-1]=np.nanquantile(pool,0.9,axis=0,method="hazen")
    clm[dd-1]=np.nanmean(pool,axis=0)
for a in (thr,clm): a[59]=(a[58]+a[60])/2
def sm(a):
    return sum(np.roll(a,-k,axis=0) for k in range(-15,16))/31
thr=sm(thr)
v=tg.values.astype("float64")
sea=np.isfinite(v).all(0)
tdoy=cum[pd.DatetimeIndex(tg.time.values).month-1]+pd.DatetimeIndex(tg.time.values).day
hot=(v>=thr[tdoy-1])&sea
def runs(h,minlen):
    out=np.zeros_like(h)
    for a in range(h.shape[1]):
        for b in range(h.shape[2]):
            x=h[:,a,b];n=len(x);k=0
            while k<n:
                if x[k]:
                    e=k
                    while e<n and x[e]: e+=1
                    if e-k>=minlen: out[k:e,a,b]=True
                    k=e
                else:k+=1
    return out
core=runs(hot,5)
m=core.copy()
for a in range(60):
    for b in range(60):
        x=core[:,a,b];idx=np.where(x)[0]
        for p0,p1 in zip(idx[:-1],idx[1:]):
            if 1<p1-p0-1<=2 or p1-p0-1 in(1,2): m[p0:p1,a,b]=True
act=m.any((1,2))
tl=pd.DatetimeIndex(tg.time.values)
ev=[];k=0
while k<len(act):
    if act[k]:
        e=k
        while e+1<len(act) and act[e+1]: e+=1
        ev.append({"onset":str(tl[k].date()),"end":str(tl[e].date())});k=e+1
    else:k+=1
print(sea.sum(),ev)
import os,json
os.makedirs("output",exist_ok=True)
xr.Dataset({"mhw":(("time","lat","lon"),m.astype("uint8"))},coords={"time":tg.time.values,"lat":la[i],"lon":lo[j]}).to_netcdf("output/mhw_mask.nc")
json.dump({"region":{"lat_min":56.63,"lat_max":57.83,"lon_min":20.23,"lon_max":21.43},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2008-06-01","end":"2008-08-31"},"events":ev,"complete":True,"caveats":""},open("output/report.json","w"))