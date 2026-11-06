import numpy as np, datetime as dt, json, warnings
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

# corrected expectations
tests = [
 ('1111100000111110000000000', [(0,4),(10,14)]),      # gap 5 -> separate
 ('1111100000011111100000000', [(0,4),(11,16)]),      # gap 6 -> separate
 ('1111100011111110000000000', [(0,4),(8,14)]),       # gap 3 -> separate
 ('1111110001111110000000000', [(0,5),(9,14)]),       # gap 3 -> separate
 ('1111110011111100000000000', [(0,13)]),             # gap 2 -> joined
 ('1111110111111100000000000', [(0,12)]),             # gap 1 -> joined
 ('11111100111110000011111000',[(0,12),(19,23)]),     # gap1 join; then gap 6 separate
 ('0000011110000001111100000', [(15,19)]),            # 4-run dropped
 ('11111011011111101111100000',[(0,4),(9,14),(16,20)]),# short gap-run ignored; gaps 4,1? runs:(0,4),(6,7)drop,(9,14),(16,20) gaps 4,1
 ('0000000000', []),                                   # nothing
 ('1111111111', [(0,9)]),                              # single run
 ('1111100000011110000011111',[(0,4),(10,14),(20,24)]),# gaps 5,5 -> three events
 ('1111100111111000001111100',[(0,14)]),               # runs (0,4),(7,12): gap 2 join; (19,23) len5 gap 6 -> separate
]
allok=True
for h,exp in tests:
    hb=np.array([c=='1' for c in h])
    got=cell_mhw_intervals(hb)
    ok = got==exp
    allok &= ok
    print('PASS' if ok else 'FAIL', h, '->', got)
print('ALL SYNTHETIC TESTS PASS:', allok)

# manual Hazen quantile check: day 153, cell (30,30)
Barr = np.load('/work/baseline_sst.npy')
cdates=[dt.date(1991,12,27)+dt.timedelta(i) for i in range(Barr.shape[0])]
CUM=[0,31,60,91,121,152,182,213,244,274,305,335]
mdoy=lambda c: CUM[c.month-1]+c.day
md=np.array([mdoy(c) for c in cdates]); ib=np.array([dt.date(1992,1,1)<=c<=dt.date(2002,12,31) for c in cdates])
ci=np.flatnonzero(ib&(md==153))
idx=np.unique(np.concatenate([np.arange(i-5,i+6) for i in ci]))
pool=Barr[idx][:,30,30]; pool=pool[np.isfinite(pool)]
n=pool.size; s=np.sort(pool)
h=(n-1)*0.9+1
lo=int(np.floor(h)); frac=h-lo
manual=(1-frac)*s[lo-1]+frac*s[lo] if frac>0 else s[lo-1]
thr_s=np.load('/work/thr_s.npy')
print('pool n:', n, 'hazen rank h:', h, 'manual raw thr d153:', manual)
print('stored (smoothed) d153 cell(30,30):', thr_s[152,30,30], '(expected close but not equal due to 31d smoothing)')
# verify raw (unsmoothed)
thr_raw=np.load('/work/thr_raw.npy')
print('stored RAW d153:', thr_raw[152,30,30], 'matches manual:', abs(manual-thr_raw[152,30,30])<1e-10)
# clim manual
clim_raw=np.load('/work/clim_raw.npy')
print('clim manual:', pool.mean(), 'stored raw:', clim_raw[152,30,30], 'match:', abs(pool.mean()-clim_raw[152,30,30])<1e-10)
# day60 rule check
print('day60 == mean(d59,d61) [thr]:', np.allclose(thr_raw[59], 0.5*(thr_raw[58]+thr_raw[60]), equal_nan=True))
