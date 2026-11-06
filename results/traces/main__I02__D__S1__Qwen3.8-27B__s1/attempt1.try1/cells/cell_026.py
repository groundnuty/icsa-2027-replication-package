import numpy as np, datetime as dt
import warnings; warnings.filterwarnings('ignore')

S_base = np.load('/work/S_base.npy'); S_tgt = np.load('/work/S_tgt.npy').reshape(92,-1)
cr = np.load('/work/coords.npz')
base_dates = [dt.date.fromisoformat(str(d)) for d in cr['baseline_dates'].astype('datetime64[D]').astype(object)]
thr_s = np.load('/work/thr_s.npy')

def doy(d):
    cum=[0]
    for L in [31,29,31,30,31,30,31,31,30,31,30,31]: cum.append(cum[-1]+L)
    return cum[d.month-1]+d.day

# --- (b) pool membership spot checks
date_to_idx = {d:i for i,d in enumerate(base_dates)}
def pool_dates(d):
    s = set()
    for y in range(1992, 2003):
        # baseline date with doy d in year y
        b = None
        for cand in [dt.date(y,1,1)+dt.timedelta(days=k) for k in range(370)]:
            if cand.year == y and doy(cand) == d:
                b = cand; break
        assert b is not None, (d,y)
        for k in range(-5,6):
            s.add(b+dt.timedelta(days=k))
    return sorted(s)

p1 = pool_dates(1)
print("d=1 pool: n=", len(p1), "first:", p1[0], "last:", p1[-1])
print(" d=1 first year window:", p1[:11])
p59 = pool_dates(59)
# 1996 (leap) window for Feb 28: Feb23..Mar5 -> includes Feb29 (doy60), Mar1-5
w1996 = [d for d in p59 if d.year==1996]
print("d=59 1996 window:", w1996)
p61 = pool_dates(61)
w1996b = [d for d in p61 if d.year==1996]
print("d=61 1996 window:", w1996b)
assert dt.date(1996,2,29) in p59 and dt.date(1996,2,29) in p61
assert dt.date(2000,2,29) in p59 and dt.date(2000,2,29) in p61
assert dt.date(1992,2,29) in p59 and dt.date(1992,2,29) in p61
# pools only within 1991-12-27..2003-01-05
allp = pool_dates(1)+pool_dates(366)
assert min(allp) >= dt.date(1991,12,27) and max(allp) <= dt.date(2003,1,5)
print("pool checks OK")

# --- (a) independent manual threshold for several (d, cell), then compare to pipeline pre-smooth thr
# recompute pre-smooth thr for a few cells/day by hand from scratch (no shared code)
import statistics
cells = [100, 1234, 2088, 3500]
for c in cells:
    r, cc = divmod(c, 60)
    for d in [153, 196, 244]:
        dates = pool_dates(d)
        vals = [S_base[date_to_idx[x], r, cc] for x in dates]
        vals = [v for v in vals if np.isfinite(v)]
        vals.sort()
        n = len(vals)
        h = (n+1)*0.9
        if n == 1 or h == int(h):
            q = vals[int(h)-1]
        else:
            lo = int(h); q = vals[lo-1] + (h-lo)*(vals[lo]-vals[lo-1])
        # pipeline value: recompute thr[d-1, c] quickly? We saved only thr_s. Recompute raw thr for these 3 d's:
print("(manual values computed; will compare below after rebuilding raw thr)")
