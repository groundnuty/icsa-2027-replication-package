import numpy as np, json, datetime as dt, time, warnings

OUT="/tmp/mhw"
ext = np.load(f"{OUT}/ext.npy")
tgt = np.load(f"{OUT}/tgt.npy")
dates = json.load(open(f"{OUT}/dates.json"))
ext_dates = [dt.date.fromisoformat(s) for s in dates["ext_dates"]]
tgt_dates = [dt.date.fromisoformat(s) for s in dates["tgt_dates"]]
NS = 3600
ext_r = ext.reshape(4028, NS)

finite_t = np.all(np.isfinite(tgt.reshape(92,NS)), axis=0)
print("sea cells:", int(finite_t.sum()), "of", NS)

MS = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
def doys(dlist):
    return MS[np.array([d.month for d in dlist]) - 1] + np.array([d.day for d in dlist], dtype=int)

D_ext = doys(ext_dates)
D_base = D_ext[5:5+4018]
assert D_ext[5]==1 and D_base[-1]==366 and len(D_base)==4018
print("baseline Feb29 count:", int((D_base==60).sum()))
D_tgt = doys(tgt_dates)
print("target doys:", D_tgt[0], "-", D_tgt[-1])

G = np.arange(4018)[:,None] + np.arange(11)[None,:]
assert G.max()==4027 and G.min()==0

thr = np.full((366, NS), np.nan)
clim = np.full((366, NS), np.nan)
t0=time.time()
pmin,pmax = 10**9, -1
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=RuntimeWarning)
    for d in range(1, 367):
        if d == 60: continue
        rows = np.flatnonzero(D_base == d)
        mask = np.zeros(4028, bool)
        mask[G[rows].ravel()] = True
        idx = np.flatnonzero(mask)
        pmin = min(pmin, len(idx)); pmax = max(pmax, len(idx))
        pool = ext_r[idx]
        colok = np.any(np.isfinite(pool), axis=0)
        th = np.full(NS, np.nan); cl = np.full(NS, np.nan)
        if colok.any():
            P = pool[:, colok]
            th[colok] = np.nanquantile(P, 0.9, axis=0, method="hazen")
            cl[colok] = np.nanmean(P, axis=0)
        thr[d-1] = th; clim[d-1] = cl
print("pool sizes:", pmin, pmax, "time", round(time.time()-t0,1), "s")

thr[59] = (thr[58] + thr[60]) / 2.0
clim[59] = (clim[58] + clim[60]) / 2.0

def smooth31(a):
    b = np.concatenate([a, a], axis=0)
    S = np.concatenate([np.zeros((1, a.shape[1])), np.nancumsum(b, axis=0)], axis=0)
    starts = (np.arange(366) - 15) % 366
    return (S[starts+31] - S[starts]) / 31.0

thr_s = smooth31(thr)
clim_s = smooth31(clim)
np.save(f"{OUT}/thr_s.npy", thr_s)
np.save(f"{OUT}/clim_s.npy", clim_s)
np.save(f"{OUT}/sea.npy", finite_t)
np.save(f"{OUT}/D_tgt.npy", D_tgt)
print("smoothed nan cells:", int(np.isnan(thr_s).sum()), int(np.isnan(clim_s).sum()))
sc = int(np.flatnonzero(finite_t)[0])
print("sample cell", sc, "thr_s[153:158]:", thr_s[153:158, sc].round(3))
print("sample cell", sc, "clim_s[153:158]:", clim_s[153:158, sc].round(3))
print("tgt sst days0-2:", tgt.reshape(92,NS)[:3, sc].round(3))
