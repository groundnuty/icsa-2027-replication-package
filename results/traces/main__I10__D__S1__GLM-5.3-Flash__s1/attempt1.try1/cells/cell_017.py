import numpy as np, warnings
warnings.filterwarnings('ignore')

def runs_of_true(h):
    idx=np.flatnonzero(h)
    if idx.size==0: return []
    br=np.flatnonzero(np.diff(idx)>1)
    return list(zip(np.concatenate([[idx[0]],idx[br+1]]).tolist(),
                    np.concatenate([idx[br],[idx[-1]]]).tolist()))
def cell_mhw_intervals(h):
    runs=[(s,e) for s,e in runs_of_true(h) if e-s+1>=5]
    if not runs: return []
    merged=[list(runs[0])]
    for s,e in runs[1:]:
        if s-merged[-1][1]-1 <= 2: merged[-1][1]=e
        else: merged.append([s,e])
    return [(s,e) for s,e in merged]

# corrected expectations (runs of >=5 only; join gaps 1-2)
tests = [
 ('1111100000111110000000000', [(0,4),(10,14)]),
 ('1111100000011111100000000', [(0,4),(11,16)]),
 ('1111100011111110000000000', [(0,4),(8,14)]),
 ('1111110001111110000000000', [(0,5),(9,14)]),
 ('1111110011111100000000000', [(0,13)]),
 ('1111110111111100000000000', [(0,13)]),        # runs (0,5),(7,13): gap1 -> join
 ('11111100111110000011111000',[(0,12),(18,22)]),
 ('0000011110000001111100000', [(15,19)]),
 ('11111011011111101111100000',[(0,4),(9,20)]),  # runs (0,4),(9,14),(16,20): gap4 sep, gap1 join
 ('0000000000', []),
 ('1111111111', [(0,9)]),
 ('1111100000011110000011111',[(0,4),(20,24)]),  # middle run len4 dropped
 ('1111100111111000001111100',[(0,12),(18,22)]), # gap2 join; then gap5 sep
 ('1111100000111110011111100',[(0,4),(10,22)]),  # first gap5 sep; second gap2 join
]
allok=True
for h,exp in tests:
    hb=np.array([c=='1' for c in h]); got=cell_mhw_intervals(hb)
    ok=got==exp; allok&=ok
    if not ok: print('FAIL', h, '->', got, 'exp', exp)
print('ALL SYNTHETIC TESTS PASS:', allok)

# --- Hazen (type 5) manual check ---
def hazen_manual(pool_sorted, q):
    n=pool_sorted.size
    h = n*q + 0.5            # 1-based rank, Hyndman-Fan type 5
    lo=int(np.floor(h))
    if lo<1: return pool_sorted[0]
    if lo>=n: return pool_sorted[-1]
    g=h-lo
    return (1-g)*pool_sorted[lo-1] + g*pool_sorted[lo]
rng=np.random.default_rng(7)
ok=True
for _ in range(50):
    n=rng.integers(20,300); x=rng.normal(size=n)
    x[rng.integers(0,n,size=5)]=np.nan
    xs=np.sort(x[~np.isnan(x)])
    for q in [0.0,0.05,0.5,0.9,0.95,1.0]:
        a=np.nanquantile(x,q,method='hazen'); b=hazen_manual(xs,q)
        ok &= abs(a-b)<1e-12
print('np.nanquantile(hazen) == manual type-5 on random pools:', ok)

# day-153, cell(30,30) exact re-derivation
import datetime as dt
Barr=np.load('/work/baseline_sst.npy')
CUM=[0,31,60,91,121,152,182,213,244,274,305,335]
cdates=[dt.date(1991,12,27)+dt.timedelta(i) for i in range(Barr.shape[0])]
md=np.array([CUM[c.month-1]+c.day for c in cdates])
ib=np.array([dt.date(1992,1,1)<=c<=dt.date(2002,12,31) for c in cdates])
ci=np.flatnonzero(ib&(md==153))
idx=np.unique(np.concatenate([np.arange(i-5,i+6) for i in ci]))
pool=np.sort(Barr[idx][:,30,30][np.isfinite(Barr[idx][:,30,30])])
m=hazen_manual(pool,0.9)
thr_raw=np.load('/work/thr_raw.npy')
print('manual hazen d153 cell(30,30):', m, '| stored raw:', thr_raw[152,30,30],
      '| exact match:', m==thr_raw[152,30,30])
# also one random baseline day+cell fully re-derived vs raw arrays
d2, r2, c2 = 200, 17, 41
ci2=np.flatnonzero(ib&(md==d2)); idx2=np.unique(np.concatenate([np.arange(i-5,i+6) for i in ci2]))
p2=Barr[idx2][:,r2,c2]
thr2=np.nanquantile(p2,0.9,axis=0,method='hazen'); cl2=np.nanmean(p2)
print(f'random check d{d2} cell({r2},{c2}): thr match:', thr2==thr_raw[d2-1,r2,c2],
      '| clim match:', abs(cl2-np.load("/work/clim_raw.npy")[d2-1,r2,c2])<1e-12)
