import numpy as np, datetime as dt, pickle

data=np.load('/work/data_region.npy')
with open('/work/all_dates.pkl','rb') as fh: dates=pickle.load(fh)
with open('/work/pool_idx.pkl','rb') as fh: pool_idx=pickle.load(fh)
z=np.load('/work/raw.npz'); thr_raw=z['thr_raw']
fin=np.load('/work/final.npz'); sea=fin['sea']
CUM_LEAP=np.array([0,31,60,91,121,152,182,213,244,274,305,335])

def hazen_t5(x):
    x=np.sort(x[np.isfinite(x)]); n=x.size
    g=n*0.9-0.5
    lo=int(np.floor(g)); frac=g-lo
    if lo>=n-1: return x[n-1]
    return x[lo]*(1-frac)+x[lo+1]*frac

rng=np.random.default_rng(11)
cells=[(i,j) for i in range(60) for j in range(60) if sea[i,j]]
sample=[cells[k] for k in rng.choice(len(cells),size=12,replace=False)]
nfail=0; diffs=[]; examples=[]
for (i,j) in sample:
    for d in rng.choice(np.r_[np.arange(1,60),np.arange(61,367)],size=10,replace=False):
        v=data[pool_idx[d],i,j]
        a=thr_raw[d-1,i,j]; b=hazen_t5(v)
        if a!=b:
            nfail+=1
            diffs.append(abs(a-b))
            if len(examples)<5:
                vs=np.sort(v[np.isfinite(v)]); n=vs.size
                g=n*0.9-0.5; lo=int(np.floor(g)); frac=g-lo
                alt=vs[lo]+frac*(vs[lo+1]-vs[lo])
                examples.append((i,j,int(d),a,b,repr(float(a-b)),alt==b,'frac=%.6f'%frac))
print('failures (exact !=):', nfail, 'of 120')
print('max abs diff:', max(diffs) if diffs else 0)
for e in examples: print(e)
# relative size
print('rel diff max:', (max(diffs)/1e3) if diffs else 0)
