s=xr.open_dataset('/work/reg.nc').analysed_sst
t=pd.DatetimeIndex(s.time.values);A=s.values.astype(np.float64)
doy=lambda ix: np.array([ (pd.Timestamp(2000,m,dd).dayofyear) for m,dd in zip(ix.month,ix.day)])
D=doy(t)
bi=np.where((t>='1992-01-01')&(t<='2002-12-31'))[0]
thr=np.full((366,)+A.shape[1:],np.nan);clim=thr.copy()
for k in range(1,367):
    if k==60: continue
    c=[b for b in bi if D[b]==k]
    idx=sorted({b+o for b in c for o in range(-5,6)})
    P=A[idx]
    thr[k-1]=np.nanquantile(P,0.9,axis=0,method='hazen');clim[k-1]=np.nanmean(P,axis=0)
for a in(thr,clim): a[59]=(a[58]+a[60])/2
def sm(a): return np.mean([np.roll(a,-j,axis=0) for j in range(-15,16)],axis=0)
thr=sm(thr)
ti=np.where((t>='2003-06-01')&(t<='2003-08-31'))[0]
X=A[ti];sea=np.isfinite(X).all(0)
hot=(X>=thr[D[ti]-1])&sea
n=len(ti);m=np.zeros_like(hot)
for i in range(60):
  for j in range(60):
    if not sea[i,j]:continue
    h=hot[:,i,j];runs=[];k=0
    while k<n:
        if h[k]:
            e=k
            while e+1<n and h[e+1]:e+=1
            if e-k+1>=5:runs.append([k,e])
            k=e+1
        else:k+=1
    mer=[]
    for r in runs:
        if mer and r[0]-mer[-1][1]-1<=2: mer[-1][1]=r[1]
        else: mer.append(r)
    for a,b in mer:m[a:b+1,i,j]=True
act=m.any((1,2));ev=[];k=0
while k<n:
    if act[k]:
        e=k
        while e+1<n and act[e+1]:e+=1
        ev.append({"onset":str(t[ti[k]].date()),"end":str(t[ti[e]].date())});k=e+1
    else:k+=1
print(sea.sum(),ev)
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),m.astype('uint8'))},coords={'time':t[ti],'lat':s.latitude.values,'lon':s.longitude.values}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":60.49,"lat_max":61.69,"lon_min":17.25,"lon_max":18.45},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2003-06-01","end":"2003-08-31"},"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))