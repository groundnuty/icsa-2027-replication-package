import numpy as np, json, os, time
from datetime import date, timedelta

t0 = time.time()
data = np.load('/tmp/chunk1.npy')  # (4120, 60, 60) float64
assert data.shape == (4120, 60, 60)

def daterange(a, b):
    out=[]; d=a
    while d<=b:
        out.append(d); d+=timedelta(days=1)
    return out

bd_ext = daterange(date(1991,12,27), date(2003,1,5))   # values available (incl. extension days)
target_dates = daterange(date(2013,6,1), date(2013,8,31))
assert len(bd_ext) + len(target_dates) == 4120
dates = bd_ext + target_dates
assert dates[0]==date(1991,12,27) and dates[4027]==date(2002,12,31) and dates[4028]==date(2003,1,1)
assert dates[4028+91]==date(2013,8,31)

cum = [0,31,60,91,121,152,182,213,244,274,305,335]  # cumulative days before month (leap-style, month/day mapping)
def key(dt): return cum[dt.month-1] + dt.day
# sanity checks of key mapping
for dt,k in [(date(1992,1,1),1),(date(1993,2,28),59),(date(1992,2,29),60),(date(1994,3,1),61),(date(2000,12,31),366),(date(1993,12,31),366)]:
    assert key(dt)==k, (dt, key(dt), k)
tk = [key(d) for d in target_dates]
assert tk[0]==153 and tk[-1]==244 and tk==list(range(153,245))

idx_of = {dt: i for i, dt in enumerate(bd_ext)}
NBASE = len(bd_ext)  # 4028
V = data[:NBASE]          # baseline values (incl. extension days as pool candidates)
TGT = data[NBASE:]        # (92, 60, 60)
NC = 3600

# --- sea cells: finite on every target day ---
sea = np.isfinite(TGT).all(axis=0)          # (60,60)
print("sea cells:", int(sea.sum()))
# check baseline finiteness on sea cells (informational)
print("baseline NaNs on sea cells:", int((~np.isfinite(V[:, sea])).sum()), "of", V[:, sea].size)

# --- pool index arrays per day-of-year d (1..366, d!=60) ---
pool_idx = {}
for d in range(1, 367):
    if d == 60: continue
    centers = [dt for dt in bd_ext if key(dt) == d and 1992 <= dt.year <= 2002]
    idx = []
    for s in centers:
        o = idx_of[s]
        idx.extend(range(o-5, o+6))
    idx = np.array(idx)
    assert idx.min() >= 0 and idx.max() < NBASE
    assert len(idx) == len(centers)*11
    pool_idx[d] = idx
print("pools built; sizes:", set(len(v) for v in pool_idx.values()))

# --- threshold (hazen/type5, ignore NaN) and climatology (mean, ignore NaN) ---
thr  = np.full((366, NC), np.nan)
clim = np.full((366, NC), np.nan)
cols = np.arange(NC)
for d in range(1, 367):
    if d == 60: continue
    P = V[pool_idx[d]].reshape(len(pool_idx[d]), NC)
    nf = np.isfinite(P)
    n = nf.sum(axis=0)
    S = np.sort(P, axis=0)  # NaNs sorted to the end
    h = n*0.9 + 0.5         # type 5 / hazen, 1-based
    lo = np.floor(h).astype(np.int64)
    gamma = h - lo
    i1 = np.clip(lo-1, 0, np.maximum(n-1, 0))
    i2 = np.clip(lo,   0, np.maximum(n-1, 0))
    q = (1.0-gamma)*S[i1, cols] + gamma*S[i2, cols]
    q = np.where(n > 0, q, np.nan)
    thr[d-1] = q
    with np.errstate(invalid='ignore'):
        clim[d-1] = np.nanmean(P, axis=0)

# validate manual hazen against numpy on a few pools
for d in (1, 60, 153, 244, 366):
    if d == 60: continue
    P = V[pool_idx[d]].reshape(len(pool_idx[d]), NC)[:, :37]
    ref = np.nanquantile(P, 0.9, axis=0, method='hazen')
    # recompute manual for these columns
    nf = np.isfinite(P); n = nf.sum(axis=0); S = np.sort(P, axis=0)
    h = n*0.9+0.5; lo = np.floor(h).astype(np.int64); gamma = h-lo
    i1 = np.clip(lo-1, 0, np.maximum(n-1,0)); i2 = np.clip(lo, 0, np.maximum(n-1,0))
    man = (1.0-gamma)*S[i1, np.arange(P.shape[1])] + gamma*S[i2, np.arange(P.shape[1])]
    man = np.where(n>0, man, np.nan)
    print(f"day {d}: manual==nanquantile(hazen):", np.allclose(ref, man, equal_nan=True))

# day 60 = mean of days 59 and 61 (before smoothing)
thr[59]  = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])

# --- 31-day centred moving mean, wrapping mod 366 ---
def smooth31(a):  # a: (366, NC)
    a3 = np.tile(a, (3, 1))                       # (1098, NC)
    c = np.zeros((a3.shape[0]+1, a.shape[1]))
    np.cumsum(a3, axis=0, out=c[1:])
    d0 = np.arange(366)
    s = c[d0+382] - c[d0+351]                     # sum a3[d0+351 .. d0+381]
    return s/31.0
# unit check of smoothing window on a ramp
ramp = np.arange(366, dtype=float)[:, None]*np.ones((1,1))
sm = smooth31(ramp)[:,0]
# day 1 (idx0): mean of days 352..366,1..16
expect = (np.arange(351,366).sum() + np.arange(0,16).sum())/31.0
print("smooth check day1:", np.isclose(sm[0], expect), " day200:", np.isclose(sm[199], np.arange(184,215).sum()/31.0))

thr_sm = smooth31(thr)
clim_sm = smooth31(clim)
print("thr_sm sample (day 200, few cells):", np.round(thr_sm[199,:4],4), "clim:", np.round(clim_sm[199,:4],4))
print("compute time so far: %.1fs" % (time.time()-t0))

np.savez_compressed('/tmp/stage2.npz', thr_sm=thr_sm, clim_sm=clim_sm, sea=sea,
                    tgt=TGT, tk=np.array(tk))
print("staged.")
