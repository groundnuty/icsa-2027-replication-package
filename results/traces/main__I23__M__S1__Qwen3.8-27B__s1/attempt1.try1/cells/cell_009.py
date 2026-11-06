import numpy as np, json, datetime as dt, time, warnings

OUT="/tmp/mhw"
ext = np.load(f"{OUT}/ext.npy")      # (4028,60,60)
tgt = np.load(f"{OUT}/tgt.npy")      # (92,60,60)
dates = json.load(open(f"{OUT}/dates.json"))
ext_dates = [dt.date.fromisoformat(s) for s in dates["ext_dates"]]
tgt_dates = [dt.date.fromisoformat(s) for s in dates["tgt_dates"]]
NS = 60*60
ext_r = ext.reshape(4028, NS)

# sea cells: finite on every target day
finite_t = np.all(np.isfinite(tgt.reshape(92,NS)), axis=0)
nsea = int(finite_t.sum())
print("sea cells:", nsea, "of", NS)

# day of year (leap calendar) helper
MS = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
def doys(dlist):
    return MS[[d.month for d in dlist]] + np.array([d.day for d in dlist])

D_ext = doys(ext_dates)      # (4028,)
D_base = D_ext[5:5+4018]     # baseline dates 1992-01-01..2002-12-31
assert D_ext[5]==1 and D_base[-1]==366 and len(D_base)==4018
D_tgt = doys(tgt_dates)
print("target doys:", D_tgt[0], D_tgt[-1])

# window global indices: baseline date i (0-based in base) at ext idx 5+i, window [i, i+10]
G = np.arange(4018)[:,None] + np.arange(11)[None,:]   # (4018,11) ext-day indices
assert G.max() == 4027 and G.min() == 0

thr = np.full((366, NS), np.nan)
clim = np.full((366, NS), np.nan)
t0=time.time()
pool_sizes = {}
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=RuntimeWarning)
    for d in range(1, 367):
        if d == 60: continue
        rows = np.flatnonzero(D_base == d)
        mask = np.zeros(4028, bool)
        mask[G[rows].ravel()] = True
        idx = np.flatnonzero(mask)
        pool_sizes[d] = len(idx)
        pool = ext_r[idx]                      # (k, NS)
        # columns that have >=1 finite
        colok = np.any(np.isfinite(pool), axis=0)
        th = np.full(NS, np.nan); cl = np.full(NS, np.nan)
        if colok.any():
            P = pool[:, colok]
            th[colok] = np.nanquantile(P, 0.9, axis=0, method="hazen")
            cl[colok] = np.nanmean(P, axis=0)
        thr[d-1] = th; clim[d-1] = cl
print("pools:", min(pool_sizes.values()), max(pool_sizes.values()),
      "set:", sorted(set(pool_sizes.values())), "time", round(time.time()-t0,1), "s")

# day 60 = mean of 59 and 61
thr[59] = (thr[58] + thr[60]) / 2.0
clim[59] = (clim[58] + clim[60]) / 2.0

# 31-day centred circular moving mean
def smooth31(a):
    # a: (366, NS)
    b = np.concatenate([a, a], axis=0)
    S = np.concatenate([np.zeros((1, a.shape[1])), np.nancumsum(b, axis=0)], axis=0)
    starts = (np.arange(366) - 15) % 366
    out = (S[starts+31] - S[starts]) / 31.0
    return out

thr_s = smooth31(thr)
clim_s = smooth31(clim)
np.save(f"{OUT}/thr_s.npy", thr_s)
np.save(f"{OUT}/clim_s.npy", clim_s)
np.save(f"{OUT}/sea.npy", finite_t)
np.save(f"{OUT}/D_tgt.npy", D_tgt)
print("thr_s nan cells:", int(np.isnan(thr_s).sum()), "clim_s nan cells:", int(np.isnan(clim_s).sum()))
# sanity: print one sea cell's June threshold vs raw sst
sc = np.flatnonzero(finite_t)[0]
print("cell", sc, "lat/lon idx:", sc//60, sc%60)
print("thr_s doy153..160:", thr_s[153:160, sc].round(3))
print("clim_s doy153..160:", clim_s[153:160, sc].round(3))
print("tgt sst first days:", tgt.reshape(92,NS)[:3, sc].round(3))
