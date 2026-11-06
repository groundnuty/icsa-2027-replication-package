import numpy as np, time, json, warnings
from datetime import date, timedelta
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
print("target doys:", doy_t[0], "..", doy_t[-1], "| ndates baseline-ext:", nd)

# sanity: convolve centering
a=np.zeros(20); a[10]=1; c=np.convolve(a,np.ones(5),'same')
assert np.flatnonzero(c>0).tolist()==[8,9,10,11,12], "convolve centering unexpected"

# pools via ±5-day dilation of doy marks
P=np.zeros((366,nd),bool); ones11=np.ones(11)
for d in range(1,367):
    if d==60: continue
    P[d-1]=np.convolve((doy_b==d).astype(float),ones11,'same')>0
ps=P.sum(1)
print("pool sizes: doy1=%d doy59=%d doy60=%d doy61=%d doy153=%d doy366=%d; min/max excl60=%d/%d" %
      (ps[0],ps[58],ps[59],ps[60],ps[152],ps[365],ps[ps>0].min(),ps.max()))

# brute-force verification of pools for selected doys
bdates_py=[d0b.item()+timedelta(days=i) for i in range(nd)]
def doy_of_date(dt): return int(cum[dt.month-1]+dt.day)
ok=True
for dd in (1,2,59,60,61,152,153,244,365,366):
    marks=[i for i,dt in enumerate(bdates_py) if 1992<=dt.year<=2002 and doy_of_date(dt)==dd]
    s=set()
    for i in marks:
        for k in range(-5,6):
            j=i+k
            if 0<=j<nd: s.add(j)
    match = (P[dd-1].sum()==len(s)) and (np.flatnonzero(P[dd-1]).tolist()==sorted(s))
    if dd!=60: ok &= bool(match)
    print("doy %3d: marks=%d pool=%d match=%s" % (dd,len(marks),len(s),match))
print("brute-force pool check (excl doy60): passed =",ok)
print("doy-60 marked dates:", [str(dates_b[i]) for i in np.flatnonzero(doy_b==60)])

# hazen reference examples
for v,p in [([0.,1.,2.,3.],0.5),([0.,1.,2.,3.],0.9),([0.,1.],0.9),([0.,1.,2.],0.9)]:
    print("np.quantile hazen", v, p, "=", round(float(np.quantile(v,p,method='hazen')),6))

# thresholds & climatology per sea cell
W=B.reshape(nd,-1).astype(np.float64); Wt=T.reshape(nt,-1).astype(np.float64)
sea=sea_all.reshape(-1); sea_cols=np.flatnonzero(sea)
Ws=W[:,sea_cols]
assert np.isfinite(Ws).all() and np.isfinite(Wt[:,sea_cols]).all()
nsea=sea_cols.size
thresh=np.empty((366,nsea)); clim=np.empty_like(thresh)
t0=time.time()
for d in range(1,367):
    if d==60: continue
    X=Ws[P[d-1]]
    thresh[d-1]=np.quantile(X,0.9,axis=0,method='hazen')
    clim[d-1]=X.mean(axis=0)
print("raw pools done %.1fs" % (time.time()-t0))
thresh[59]=0.5*(thresh[58]+thresh[60]); clim[59]=0.5*(clim[58]+clim[60])
def circ31(X):
    Y=np.zeros_like(X)
    for k in range(-15,16): Y+=np.roll(X,k,axis=0)
    return Y/31.0
thresh_s=circ31(thresh); clim_s=circ31(clim)
assert np.isfinite(thresh_s).all() and np.isfinite(clim_s).all()
jja=np.arange(152,244)
print("smoothed threshold (doys153-244): min %.4f max %.4f | clim: min %.4f max %.4f" %
      (thresh_s[jja].min(),thresh_s[jja].max(),clim_s[jja].min(),clim_s[jja].max()))
print("doy200: mean thresh %.4f mean clim %.4f | thresh>=clim cells: %d/%d" %
      (thresh_s[199].mean(),clim_s[199].mean(),int((thresh_s[199]>=clim_s[199]).sum()),nsea))

# hot days, per-cell MHWs
hot=Wt[:,sea_cols]>=thresh_s[doy_t-1]
print("hot day fraction over sea cells: %.4f" % hot.mean())
hotT=np.ascontiguousarray(hot.T)
mem=np.zeros((nt,nsea),bool); n_mhw=0; lens=[]
for c in range(nsea):
    idx=np.flatnonzero(hotT[c])
    if idx.size==0: continue
    br=np.flatnonzero(np.diff(idx)>1)
    starts=np.r_[idx[0],idx[br+1]]; ends=np.r_[idx[br],idx[-1]]
    runs=[[int(s),int(e)] for s,e in zip(starts,ends) if e-s+1>=5]
    merged=[]
    for s,e in runs:
        if merged and 1<=s-merged[-1][1]-1<=2: merged[-1][1]=e
        else: merged.append([s,e])
    for s,e in merged:
        mem[s:e+1,c]=True; lens.append(e-s+1)
    n_mhw+=len(merged)
print("per-cell MHWs: n=%d | cells with >=1 MHW: %d/%d | total MHW days: %d | len min/median/max: %d/%d/%d" %
      (n_mhw,int(mem.any(axis=0).sum()),nsea,int(mem.sum()),min(lens),int(np.median(lens)),max(lens)))

# regional events
active=mem.any(axis=1)
idx=np.flatnonzero(active)
events=[]
if idx.size:
    br=np.flatnonzero(np.diff(idx)>1)
    starts=np.r_[idx[0],idx[br+1]]; ends=np.r_[idx[br],idx[-1]]
    events=[[int(s),int(e)] for s,e in zip(starts,ends)]
print("active days: %d/92" % int(active.sum()))
ev_dates=[[str(dates_t[s]),str(dates_t[e])] for s,e in events]
for (s,e),ds in zip(events,ev_dates):
    print("event %s..%s len=%d | cells-in-MHW min/max per day: %d/%d" %
          (ds[0],ds[1],e-s+1,int(mem[s:e+1].sum(axis=1).min()),int(mem[s:e+1].sum(axis=1).max())))
np.savez('/tmp/results.npz',mem=mem,hot=hot,thresh_s=thresh_s,clim_s=clim_s,
         events=np.array(events,int),active=active,doy_t=doy_t)
print("total %.1fs" % (time.time()-t00))
