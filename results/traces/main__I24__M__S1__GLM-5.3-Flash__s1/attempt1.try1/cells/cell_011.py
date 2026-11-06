import numpy as np, datetime as dt
A=np.load('/tmp/A_all.npy'); ords=np.load('/tmp/dates_ord.npy')
dates=[dt.date.fromordinal(int(o)) for o in ords]
T=A.shape[0]; Aflat=A.reshape(T,-1)
def doy_map(d):
    y=d.timetuple().tm_yday
    leap = d.year%4==0 and (d.year%100!=0 or d.year%400==0)
    return y if leap else (y+1 if y>=60 else y)
doy=np.array([doy_map(d) for d in dates])
b0=dt.date(1992,1,1); b1=dt.date(2002,12,31)
base_idx=np.array([i for i,d in enumerate(dates) if b0<=d<=b1])
list_d={d: base_idx[doy[base_idx]==d] for d in range(1,367)}
offs=np.arange(-5,6)
c=118; d=2
idxs=list_d[d]
P=Aflat[idxs[:,None]+offs[None,:], c]
print('pool size',P.size,'finite',np.isfinite(P).sum())
vals=np.sort(P[np.isfinite(P)])
print('sorted finite vals (first 20):', vals[:20])
print('n:',len(vals))
q=np.quantile(vals,0.9,method='hazen')
print('np hazen:',repr(q))
# manual type-5
nv=len(vals); pos=(nv-1)*0.9; k=int(np.floor(pos)); g=pos-k
print('manual:', repr(vals[k]+g*(vals[k+1]-vals[k]) if g>0 else vals[k]), 'k',k,'g',g)
thr_raw=np.load('/tmp/thr_raw.npy')
print('stored:',repr(thr_raw[d-1,c]))
# which finite days for this cell?
fin_days=[dates[i] for i in range(T) if np.isfinite(Aflat[i,c])]
print('cell118 finite days: first/last', fin_days[0], fin_days[-1], 'count', len(fin_days))
