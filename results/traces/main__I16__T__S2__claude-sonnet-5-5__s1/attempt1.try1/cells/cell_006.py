
for a in (thr,clim): a[59]=(a[58]+a[60])/2
def sm(a):
    return sum(np.roll(a,-k,axis=0) for k in range(-15,16))/31
thr=sm(thr)
T=t.values.astype('float64');tt=pd.DatetimeIndex(t.time.values);td=doy(tt)
sea=np.isfinite(T).all(0)
hot=(T>=thr[td-1])&sea
out=np.zeros(hot.shape,bool)
for i in range(ny):
  for j in range(nx):
    if not sea[i,j]: continue
    h=hot[:,i,j];lab,n=label(h)
    runs=[(np.where(lab==k)[0][0],np.where(lab==k)[0][-1]) for k in range(1,n+1) if (lab==k).sum()>=5]
    m=np.zeros(len(h),bool)
    for k,(s,e) in enumerate(runs):
        m[s:e+1]=True
        if k+1<len(runs) and runs[k+1][0]-e-1<=2: m[e:runs[k+1][0]]=True
    out[:,i,j]=m
act=out.any((1,2));lab,n=label(act)
ev=[{"onset":str(tt[np.where(lab==k)[0][0]].date()),"end":str(tt[np.where(lab==k)[0][-1]].date())} for k in range(1,n+1)]
print(sea.sum(),ev)
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),out.astype('uint8'))},coords={'time':t.time.values,'lat':t.latitude.values,'lon':t.longitude.values}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":56.63,"lat_max":57.83,"lon_min":20.23,"lon_max":21.43},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2008-06-01","end":"2008-08-31"},"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))
