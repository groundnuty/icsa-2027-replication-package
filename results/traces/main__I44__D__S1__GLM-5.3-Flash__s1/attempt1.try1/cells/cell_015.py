import numpy as np, datetime as dt, pickle, json

data=np.load('/work/data_region.npy')
with open('/work/all_dates.pkl','rb') as fh: dates=pickle.load(fh)
with open('/work/pool_idx.pkl','rb') as fh: pool_idx=pickle.load(fh)
fin=np.load('/work/final.npz')
sea=fin['sea']; hot=fin['hot']; mhw=fin['mhw']; active=fin['active']
d0=dates[0]; N=len(dates)
t_start=dt.date(2004,6,1)
CUM_LEAP=np.array([0,31,60,91,121,152,182,213,244,274,305,335])
def doy_of(d): return int(CUM_LEAP[d.month-1]+d.day)

# --- 1) independent pool construction by reversed mapping: baseline date bd contributes to pools of doy(bd+o), o=-5..5
rev={d:set() for d in range(1,367)}
bi0=(dt.date(1992,1,1)-d0).days; bi1=(dt.date(2002,12,31)-d0).days
for i in range(bi0,bi1+1):
    bd=d0+dt.timedelta(days=i)
    for o in range(-5,6):
        j=i+o
        if 0<=j<N:
            dd=doy_of(d0+dt.timedelta(days=j))
            rev[dd].add(j)
rev={k:np.array(sorted(v)) for k,v in rev.items() if k!=60}
mismatch=[d for d in rev if not np.array_equal(rev[d], pool_idx[d])]
print('pool cross-check (reversed mapping) mismatches:', mismatch)

# --- 2) manual Hazen p90 vs np.nanpercentile hazen, on raw pools for sample cells
rng=np.random.default_rng(7)
cells=[(i,j) for i in range(60) for j in range(60) if sea[i,j]]
sample=[cells[k] for k in rng.choice(len(cells), size=10, replace=False)]
def hazen_manual(x):
    x=x[np.isfinite(x)]
    x=np.sort(x)
    n=x.size
    pos=0.9*(n-1)          # 0-based position
    lo=int(np.floor(pos)); frac=pos-lo
    if lo>=n-1: return x[n-1]
    return x[lo]*(1-frac)+x[lo+1]*frac
z=np.load('/work/raw.npz'); thr_raw=z['thr_raw']; clim_raw=z['clim_raw']  # 0-based doy
okq=True; okm=True
for (i,j) in sample:
    for d in rng.choice(np.arange(1,367)[np.arange(1,367)!=60], size=8, replace=False):
        v=data[pool_idx[d], i, j]
        if hazen_manual(v)!=thr_raw[d-1,i,j]: okq=False
        if np.nanmean(v)!=clim_raw[d-1,i,j]: okm=False
print('manual hazen matches:', okq, '| manual mean matches:', okm)

# --- 3) brute-force full pipeline for sample cells (independent smoothing + detection)
def circ_bf(a):  # a: (366,) for one cell
    out=np.empty(366)
    for k in range(366):
        idxs=[(k+o)%366 for o in range(-15,16)]
        out[k]=a[idxs].mean()
    return out
def runs_bf(h):
    # returns mhw bool via explicit scanning
    n=h.size; m=np.zeros(n,bool)
    i=0
    runs=[]
    while i<n:
        if h[i]:
            j=i
            while j+1<n and h[j+1]: j+=1
            runs.append((i,j)); i=j+1
        else: i+=1
    keep=[(a,b) for a,b in runs if b-a+1>=5]
    if not keep: return m
    merged=[list(keep[0])]
    for a,b in keep[1:]:
        if a-merged[-1][1]-1<=2: merged[-1][1]=b
        else: merged.append([a,b])
    for a,b in merged: m[a:b+1]=True
    return m
okfull=True
for (i,j) in sample:
    tr=np.full(366,np.nan); cl=np.full(366,np.nan)
    for d in range(1,367):
        if d==60: continue
        v=data[pool_idx[d],i,j]
        tr[d-1]=hazen_manual(v); cl[d-1]=v.mean()
    tr[59]=0.5*(tr[58]+tr[60]); cl[59]=0.5*(cl[58]+cl[60])
    trs=circ_bf(tr); 
    mm=np.zeros(92,bool)
    for k in range(92):
        d=doy_of(t_start+dt.timedelta(days=k))
        mm[k]= data[4540+k,i,j] >= trs[d-1]
    mbf=runs_bf(mm)
    if not np.array_equal(mbf, mhw[:,i,j]): okfull=False; print('MISMATCH cell',i,j)
print('brute-force full-pipeline matches on 10 sample cells:', okfull)

# --- 4) synthetic tests of run/gap logic
def cell_mhw(h):
    m=np.zeros(h.size,bool); idx=np.flatnonzero(h)
    if idx.size==0: return m
    br=np.flatnonzero(np.diff(idx)>1)
    s=np.r_[idx[0],idx[br+1]]; e=np.r_[idx[br],idx[-1]]
    keep=(e-s+1)>=5
    if not keep.any(): return m
    s=s[keep]; e=e[keep]
    ms=[int(s[0])]; me=[int(e[0])]
    for k in range(1,len(s)):
        if s[k]-me[-1]-1<=2: me[-1]=int(e[k])
        else: ms.append(int(s[k])); me.append(int(e[k]))
    for a,b in zip(ms,me): m[a:b+1]=True
    return m
tests=[
 (np.array([1,1,1,1,0,0,0,0,0],bool), np.zeros(9,bool)),
 (np.array([1,1,1,1,1,0,1,1,1,0,0],bool), np.array([1,1,1,1,1,1,1,1,1,0,0],bool)),
 (np.array([1,1,1,1,1,0,0,0,1,1,1],bool), np.array([1,1,1,1,1,0,0,0,1,1,1],bool)),
 (np.array([1,1,1,1,1,0,0,1,1,1,1,1,0,0,0,1,1,1,1,1],bool), np.array([1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,1,1,1,1,1],bool)),
 (np.array([0,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1],bool), np.array([0,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1],bool)),
]
for k,(h,exp) in enumerate(tests):
    got=cell_mhw(h)
    print('synthetic test',k,'pass:', np.array_equal(got,exp))

# --- 5) daily structure over target period
print('\ndoy : hot_cells mhw_cells active')
for k in range(92):
    hc=int(hot[k,sea].sum()); mc=int(mhw[k,sea].sum())
    if hc>0 or mc>0:
        print(t_start+dt.timedelta(days=k), 'doy', doy_of(t_start+dt.timedelta(days=k)), 'hot', hc, 'mhw', mc)
print('days with hot>0:', int((hot[:,sea].sum(axis=1)>0).sum()), '| days active:', int(active.sum()))
