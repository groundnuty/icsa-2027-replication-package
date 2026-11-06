import numpy as np, datetime as dt, json, os
days=[]
x=dt.date(1991,12,27)
while x<=dt.date(2003,1,5): days.append(x); x+=dt.timedelta(1)
nb=len(days)
x=dt.date(2019,6,1)
tgt=[]
while x<=dt.date(2019,8,31): tgt.append(x); x+=dt.timedelta(1)
alld=days+tgt
idx={d:i for i,d in enumerate(alld)}
first=np.load('/work/c/'+alld[0].strftime('%Y%m%d')+'.npz')
lat=first['lat']; lon=first['lon']
S=np.empty((len(alld),)+first['sst'].shape,np.float64)
for i,d in enumerate(alld):
    z=np.load('/work/c/'+d.strftime('%Y%m%d')+'.npz')
    assert np.array_equal(z['lat'],lat) and np.array_equal(z['lon'],lon)
    S[i]=z['sst']
print(S.shape, lat[[0,-1]], lon[[0,-1]])
ti=[idx[d] for d in tgt]
T=S[ti]
sea=np.all(np.isfinite(T),axis=0)
print('sea cells',sea.sum(),'of',sea.size)
print('days with NaN in sea baseline?', np.isnan(S[:nb][:,sea]).sum())