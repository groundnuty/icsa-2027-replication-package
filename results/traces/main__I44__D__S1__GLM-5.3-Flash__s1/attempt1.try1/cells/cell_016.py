import numpy as np, datetime as dt, pickle

data=np.load('/work/data_region.npy')
with open('/work/all_dates.pkl','rb') as fh: dates=pickle.load(fh)
with open('/work/pool_idx.pkl','rb') as fh: pool_idx=pickle.load(fh)
fin=np.load('/work/final.npz')
sea=fin['sea']; mhw=fin['mhw']
z=np.load('/work/raw.npz'); thr_raw=z['thr_raw']  # 0-based doy
d0=dates[0]; t_start=dt.date(2004,6,1)
CUM_LEAP=np.array([0,31,60,91,121,152,182,213,244,274,305,335])
def doy_of(d): return int(CUM_LEAP[d.month-1]+d.day)

# --- correct Hazen / Hyndman-Fan type 5 manual quantile: 0-based virtual index g = n*p - 0.5
def hazen_t5(x):
    x=np.sort(x[np.isfinite(x)]); n=x.size
    g=n*0.9-0.5
    lo=int(np.floor(g)); frac=g-lo
    if lo>=n-1: return x[n-1]
    if lo<0: return x[0]
    return x[lo]*(1-frac)+x[lo+1]*frac
# sanity vs numpy on small arrays with distinct values
for n in [4,5,10,121]:
    x=np.arange(1,n+1,dtype=float)
    a=np.quantile(x,0.9,method='hazen'); b=hazen_t5(x)
    print('n=',n,'numpy hazen',round(a,6),'manual t5',round(b,6),'match',np.isclose(a,b))
# also confirm type7 differs (so the test is meaningful)
x=np.arange(1,11,dtype=float)
print('n=10: hazen',np.quantile(x,0.9,method='hazen'),'linear(t7)',np.quantile(x,0.9,method='linear'),'differ:',not np.isclose(np.quantile(x,0.9,method='hazen'),np.quantile(x,0.9,method='linear')))

rng=np.random.default_rng(11)
cells=[(i,j) for i in range(60) for j in range(60) if sea[i,j]]
sample=[cells[k] for k in rng.choice(len(cells),size=12,replace=False)]
okq=True
for (i,j) in sample:
    for d in rng.choice(np.r_[np.arange(1,60),np.arange(61,367)],size=10,replace=False):
        v=data[pool_idx[d],i,j]
        if not np.isclose(hazen_t5(v),thr_raw[d-1,i,j],rtol=0,atol=0): okq=False
print('manual type-5 == pipeline raw thresholds on 120 (cell,doy) samples:', okq)

# --- brute-force END-TO-END with correct type-5 on 12 sample cells
def circ_bf(a):
    return np.array([a[(k+np.arange(-15,16))%366].mean() for k in range(366)])
def runs_bf(h):
    n=h.size; m=np.zeros(n,bool); i=0; runs=[]
    while i<n:
        if h[i]:
            j=i
            while j+1<n and h[j+1]: j+=1
            runs.append([i,j]); i=j+1
        else: i+=1
    keep=[r for r in runs if r[1]-r[0]+1>=5]
    if not keep: return m
    merged=[keep[0][:]]
    for r in keep[1:]:
        if r[0]-merged[-1][1]-1<=2: merged[-1][1]=r[1]
        else: merged.append(r[:])
    for a,b in merged: m[a:b+1]=True
    return m
okfull=True
for (i,j) in sample:
    tr=np.full(366,np.nan)
    for d in range(1,367):
        if d==60: continue
        tr[d-1]=hazen_t5(data[pool_idx[d],i,j])
    tr[59]=0.5*(tr[58]+tr[60])
    trs=circ_bf(tr)
    mm=np.zeros(92,bool)
    for k in range(92):
        mm[k]=data[4540+k,i,j]>=trs[doy_of(t_start+dt.timedelta(days=k))-1]
    if not np.array_equal(runs_bf(mm), mhw[:,i,j]): okfull=False; print('MISMATCH',i,j)
print('brute-force (correct hazen) full pipeline matches on 12 sample cells:', okfull)
