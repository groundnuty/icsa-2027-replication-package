import numpy as np, datetime as dt
import warnings; warnings.filterwarnings('ignore')
S_base = np.load('/work/S_base.npy')
cr = np.load('/work/coords.npz')
base_dates = [dt.date.fromisoformat(str(d)) for d in cr['baseline_dates'].astype('datetime64[D]').astype(object)]

def doy(d):
    cum=[0]
    for L in [31,29,31,30,31,30,31,31,30,31,30,31]: cum.append(cum[-1]+L)
    return cum[d.month-1]+d.day
base_doy = np.array([doy(d) for d in base_dates])
date_to_idx = {d:i for i,d in enumerate(base_dates)}

b_idx_by_doy = {}
for i, d in enumerate(base_dates):
    if dt.date(1992,1,1) <= d <= dt.date(2002,12,31):
        b_idx_by_doy.setdefault(base_doy[i], []).append(i)
pool_mask = np.zeros((367, len(base_dates)), dtype=bool)
for d in range(1, 367):
    if d == 60: continue
    for bi in b_idx_by_doy[d]:
        b = base_dates[bi]
        for k in range(-5, 6):
            pool_mask[d, date_to_idx[b + dt.timedelta(days=k)]] = True

def pool_dates(d):
    s = set()
    for y in range(1992, 2003):
        b = None
        for cand in [dt.date(y,1,1)+dt.timedelta(days=k) for k in range(370)]:
            if cand.year == y and doy(cand) == d:
                b = cand; break
        for k in range(-5,6):
            s.add(b+dt.timedelta(days=k))
    return sorted(s)

# check equivalence for all d (not just a few) - cheap: compare index sets
ok = True
for d in range(1, 367):
    if d == 60: continue
    pm = set(np.where(pool_mask[d])[0].tolist())
    pd_ = {date_to_idx[x] for x in pool_dates(d)}
    if pm != pd_:
        ok = False; print("MISMATCH d=", d, "only-mask:", list(pm-pd_)[:5], "only-dates:", list(pd_-pm)[:5]); break
print("pool equivalence all 365 days:", ok)

# hazen quantile with NaNs: manual vs numpy
rng = np.random.default_rng(42)
X = rng.standard_normal((121, 50)).astype(np.float64)
X[rng.random((121, 50)) < 0.3] = np.nan
for c in [0, 17, 49]:
    col = X[:, c]
    v = col[np.isfinite(col)]; v = np.sort(v)
    n = len(v); h = (n+1)*0.9
    if h == int(h):
        q = v[int(h)-1]
    else:
        lo = int(h); q = v[lo-1] + (h-lo)*(v[lo]-v[lo-1])
    qn = np.nanquantile(col, 0.9, method='hazen')
    print(f"cell {c}: manual={q:.10f} numpy={qn:.10f} match={np.isclose(q, qn)}")
# MATLAB-style cross-check of the hazen definition itself for n=121: h=(121+1)*0.9=109.8
print("n=121 h = ", 122*0.9, "-> between order stats 109 and 110 (1-based), weight 0.8 on 110th")
