import numpy as np, time, json, warnings, os
from datetime import timedelta
warnings.filterwarnings('ignore')
t00=time.time()
B=np.load('/tmp/B.npy'); T=np.load('/tmp/T.npy'); sea_all=np.load('/tmp/sea_all.npy')
nd=B.shape[0]; nt=T.shape[0]
d0b=np.datetime64('1991-12-27'); d0t=np.datetime64('2008-06-01')
dates_b=d0b+np.arange(nd).astype('timedelta64[D]')
dates_t=d0t+np.arange(nt).astype('timedelta64[D]')
cum=np.array([0,31,60,91,121,152,182,213,244,274,305,335])
def doy_arr(dates):
    y=dates.astype('datetime64[Y]'); m=dates.astype('datetime64[M]')
    return cum[(m-y).astype(int)] + ((dates-m).astype(int)+1)
doy_b=doy_arr(dates_b); doy_t=doy_arr(dates_t)
# day-of-year spot checks incl. leap and non-leap March
for s,exp in [('2008-02-28',59),('2008-02-29',60),('2008-03-01',61),('2001-03-01',61),
              ('2001-12-31',366),('1992-12-31',366),('1992-02-29',60),('2008-06-01',153),('2008-08-31',244)]:
    i=int(np.flatnonzero(dates_b==np.datetime64(s))[0]) if (dates_b==np.datetime64(s)).any() else None
    v=doy_arr(np.array([np.datetime64(s)]))[0]
    assert v==exp, (s,v,exp)
print("doy mapping spot checks OK")

# CORRECT marks: baseline dates only (1992-01-01..2002-12-31) = indices 5..4022 in this array
i_first=int(np.flatnonzero(dates_b==np.datetime64('1992-01-01'))[0])
i_last =int(np.flatnonzero(dates_b==np.datetime64('2002-12-31'))[0])
print("core baseline index range:", i_first, i_last, "count:", i_last-i_first+1)
incore=np.zeros(nd,bool); incore[i_first:i_last+1]=True
P=np.zeros((366,nd),bool); ones11=np.ones(11)
for d in range(1,367):
    if d==60: continue
    P[d-1]=np.convolve(((doy_b==d)&incore).astype(float),ones11,'same')>0
ps=P.sum(1)
print("fixed pool sizes: doy1=%d doy2=%d doy5=%d doy361=%d doy365=%d doy366=%d ; min/max excl60=%d/%d" %
      (ps[0],ps[1],ps[4],ps[360],ps[364],ps[365],ps[ps>0].min(),ps.max()))

# brute-force verification of ALL 365 pools against the spec
bdates=[d0b.item()+timedelta(days=i) for i in range(nd)]
def doy_of(dt): return int(cum[dt.month-1]+dt.day)
bad=[]
for d in range(1,367):
    if d==60: continue
    s=set()
    for i,dt in enumerate(bdates):
        if 1992<=dt.year<=2002 and doy_of(dt)==d:
            for k in range(-5,6):
                j=i+k
                if 0<=j<nd: s.add(j)
    if P[d-1].sum()!=len(s) or np.flatnonzero(P[d-1]).tolist()!=sorted(s): bad.append(d)
print("brute-force verification of all 365 pools:", "ALL MATCH" if not bad else ("MISMATCH doys: %s" % bad))
# explicit membership spot checks
def in_pool(datestr,d): return bool(P[d-1][int(np.flatnonzero(dates_b==np.datetime64(datestr))[0])])
print("1991-12-27 in doy1 pool:", in_pool('1991-12-27',1), "| 2003-01-05 in doy365 pool:", in_pool('2003-01-05',365),
      "| 2003-01-01 in doy1 pool (must be False):", in_pool('2003-01-01',1),
      "| 1991-12-31 in doy366 pool (must be False):", in_pool('1991-12-31',366),
      "| 1992-01-06 in doy1 pool:", in_pool('1992-01-06',1), "| 1992-01-07 in doy1 pool (must be False):", in_pool('1992-01-07',1))

# thresholds & climatology
W=B.reshape(nd,-1).astype(np.float64); Wt=T.reshape(nt,-1).astype(np.float64)
sea=sea_all.reshape(-1); sea_cols=np.flatnonzero(sea); nsea=sea_cols.size
Ws=W[:,sea_cols]
assert np.isfinite(Ws).all() and np.isfinite(Wt[:,sea_cols]).all()
thresh=np.empty((366,nsea)); clim=np.empty_like(thresh)
t0=time.time()
for d in range(1,367):
    if d==60: continue
    X=Ws[P[d-1]]
    thresh[d-1]=np.quantile(X,0.9,axis=0,method='hazen')
    clim[d-1]=X.mean(axis=0)
print("pools -> stats done %.1fs" % (time.time()-t0))
thresh[59]=0.5*(thresh[58]+thresh[60]); clim[59]=0.5*(clim[58]+clim[60])
def circ31(X):
    Y=np.zeros_like(X)
    for k in range(-15,16): Y+=np.roll(X,k,axis=0)
    return Y/31.0
thresh_s=circ31(thresh); clim_s=circ31(clim)
# smoothing checks: day 1 mixes 351..366+1..16 ; day 366 mixes 351..366+1..16; exact recompute for one cell
c=0
manual=np.array([thresh[(366+d-15-1)%366 if (d-15)>0 else d-15-1+366] for d in range(1,32)]).mean() if False else None
idxs=[( (0+k)%366 ) for k in range(-15,16)]
m1=thresh[idxs,c].mean()
print("manual doy1 smooth check cell0:", m1, "vs", thresh_s[0,c], "equal:", np.isclose(m1,thresh_s[0,c]))
idxs366=[(365+k)%366 for k in range(-15,16)]
print("manual doy366 smooth check cell0:", np.isclose(thresh[idxs366,c].mean(), thresh_s[365,c]))
jja=np.arange(152,244)
print("JJA smoothed thresh: %.4f..%.4f | clim: %.4f..%.4f" % (thresh_s[jja].min(),thresh_s[jja].max(),clim_s[jja].min(),clim_s[jja].max()))

# hot days & per-cell MHWs
hot=Wt[:,sea_cols]>=thresh_s[doy_t-1]
print("hot fraction: %.4f" % hot.mean())
hotT=np.ascontiguousarray(hot.T)
mem=np.zeros((nt,nsea),bool); n_mhw=0; lens=[]
for c2 in range(nsea):
    idx=np.flatnonzero(hotT[c2])
    if idx.size==0: continue
    br=np.flatnonzero(np.diff(idx)>1)
    starts=np.r_[idx[0],idx[br+1]]; ends=np.r_[idx[br],idx[-1]]
    runs=[[int(s),int(e)] for s,e in zip(starts,ends) if e-s+1>=5]
    merged=[]
    for s,e in runs:
        if merged and 1<=s-merged[-1][1]-1<=2: merged[-1][1]=e
        else: merged.append([s,e])
    for s,e in merged:
        mem[s:e+1,c2]=True; lens.append(e-s+1)
    n_mhw+=len(merged)
print("per-cell MHWs: n=%d | cells with >=1: %d | MHW days: %d | len min/med/max: %d/%d/%d" %
      (n_mhw,int(mem.any(0).sum()),int(mem.sum()),min(lens),int(np.median(lens)),max(lens)))
active=mem.any(axis=1)
idx=np.flatnonzero(active); events=[]
if idx.size:
    br=np.flatnonzero(np.diff(idx)>1)
    events=[[int(s),int(e)] for s,e in zip(np.r_[idx[0],idx[br+1]], np.r_[idx[br],idx[-1]])]
print("active days: %d/92 | events:" % int(active.sum()), [[str(dates_t[s]),str(dates_t[e])] for s,e in events])
for s,e in events:
    print("  %s..%s len=%d cells/day min..max: %d..%d" % (dates_t[s],dates_t[e],e-s+1,int(mem[s:e+1].sum(1).min()),int(mem[s:e+1].sum(1).max())))
np.savez('/tmp/results2.npz',mem=mem,hot=hot,thresh_s=thresh_s,clim_s=clim_s,
         events=np.array(events,int).reshape(-1,2),active=active,doy_t=doy_t,sea_cols=sea_cols)
print("total %.1fs" % (time.time()-t00))
