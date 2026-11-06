v=a.values.astype('float64'); ny,nx=v.shape[1:]
def doy(ix): 
    return np.array([ (x.month-1)*0+ (pd.Timestamp(2000,x.month,x.day).dayofyear) for x in ix])
D=doy(t)
bidx=np.where((t>=pd.Timestamp('1992-01-01'))&(t<=pd.Timestamp('2002-12-31')))[0]
thr=np.full((366,ny,nx),np.nan);clim=thr.copy()
for k in range(1,367):
    if k==60: continue
    c=bidx[D[bidx]==k]
    ii=np.unique(np.concatenate([c+o for o in range(-5,6)]))
    p=v[ii]
    thr[k-1]=np.nanquantile(p,0.9,axis=0,method='hazen')
    clim[k-1]=np.nanmean(p,axis=0)
for x in (thr,clim): x[59]=(x[58]+x[60])/2
def sm(x):
    return sum(np.roll(x,s,axis=0) for s in range(-15,16))/31
thr=sm(thr)
tgt=tg.time.values;tt=pd.DatetimeIndex(tgt);Dt=doy(tt)
s=tg.values.astype('float64')
sea=np.isfinite(s).all(0)
hot=(s>=thr[Dt-1])&sea
T=len(tt);m=np.zeros_like(hot)
for i in range(ny):
  for j in range(nx):
    if not sea[i,j]: continue
    h=hot[:,i,j].copy();runs=[];k=0
    while k<T:
        if h[k]:
            e=k
            while e<T and h[e]:e+=1
            if e-k>=5:runs.append([k,e-1])
            k=e
        else:k+=1
    mer=[]
    for r_ in runs:
        if mer and r_[0]-mer[-1][1]-1<=2: mer[-1][1]=r_[1]
        else: mer.append(r_)
    for a0,b0 in mer:m[a0:b0+1,i,j]=True
act=m.any((1,2));ev=[];k=0
while k<T:
    if act[k]:
        e=k
        while e+1<T and act[e+1]:e+=1
        ev.append({"onset":str(tt[k].date()),"end":str(tt[e].date())});k=e+1
    else:k+=1
print(sea.sum(),ev)
import os,json
os.makedirs('output',exist_ok=True)
xr.Dataset({'mhw':(('time','lat','lon'),m.astype('uint8'))},coords={'time':tgt,'lat':tg.latitude.values,'lon':tg.longitude.values}).to_netcdf('output/mhw_mask.nc')
json.dump({"region":{"lat_min":57.57,"lat_max":58.77,"lon_min":10.25,"lon_max":11.45},"baseline_analysed":{"start":"1992-01-01","end":"2002-12-31"},"target_analysed":{"start":"2016-06-01","end":"2016-08-31"},"events":ev,"complete":True,"caveats":""},open('output/report.json','w'))