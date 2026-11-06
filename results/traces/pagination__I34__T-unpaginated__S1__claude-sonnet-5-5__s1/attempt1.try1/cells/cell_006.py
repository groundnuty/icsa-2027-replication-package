z=np.load('/tmp/data.npz');A=z['A'];lat=z['lat'];lon=z['lon'];dd=pd.DatetimeIndex(z['dd'])
def doy(t):
    return np.array([ (pd.Timestamp(2000,x.month,x.day).dayofyear) for x in t])
base=(dd>=pd.Timestamp('1991-12-27'))&(dd<=pd.Timestamp('2003-01-05'))
tg=(dd>=pd.Timestamp('2007-06-01'))&(dd<=pd.Timestamp('2007-08-31'))
B=A[base];bd=dd[base];idx={t:i for i,t in enumerate(bd)}
bdoy=doy(bd)
core=[i for i,t in enumerate(bd) if pd.Timestamp('1992-01-01')<=t<=pd.Timestamp('2002-12-31')]
thr=np.full((366,60,60),np.nan);clim=thr.copy()
for k in range(1,367):
    if k==60: continue
    ii=set()
    for i in core:
        if bdoy[i]==k:
            for o in range(-5,6):
                t=bd[i]+pd.Timedelta(days=o)
                ii.add(idx[t])
    ii=sorted(ii)
    P=B[ii]
    thr[k-1]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim[k-1]=np.nanmean(P,axis=0)
for a in (thr,clim): a[59]=(a[58]+a[60])/2
def sm(a):
    return np.mean([np.roll(a,-s,axis=0) for s in range(-15,16)],axis=0)
thr=sm(thr)
T=A[tg];td=dd[tg]
sea=np.isfinite(T).all(0)
th=thr[doy(td)-1]
hot=(T>=th)&sea
n=len(td);mh=np.zeros_like(hot)
for i in range(60):
  for j in range(60):
    if not sea[i,j]: continue
    h=hot[:,i,j];runs=[];s=None
    for t in range(n+1):
        v=h[t] if t<n else False
        if v and s is None:s=t
        if not v and s is not None:
            if t-s>=5:runs.append([s,t-1])
            s=None
    mer=[]
    for r in runs:
        if mer and r[0]-mer[-1][1]-1<=2: mer[-1][1]=r[1]
        else: mer.append(r)
    for a,b in mer: mh[a:b+1,i,j]=True
act=mh.any((1,2));ev=[];s=None
for t in range(n+1):
    v=act[t] if t<n else False
    if v and s is None:s=t
    if not v and s is not None: ev.append({"onset":str(td[s].date()),"end":str(td[t-1].date()));s=None}
print(sea.sum(),ev,len(td),np.isnan(thr[:,sea]).sum())
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),mh.astype('uint8'))},coords={'time':td.values,'lat':lat,'lon':lon}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":59.93,"lat_max":61.13,"lon_min":18.69,"lon_max":19.89},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2007-06-01","end":"2007-08-31"},"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))