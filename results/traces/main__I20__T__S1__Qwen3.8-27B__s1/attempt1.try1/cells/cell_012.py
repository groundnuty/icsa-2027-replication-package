import numpy as np, pickle

D = pickle.load(open("/tmp/mhw_data.pkl","rb"))
M = pickle.load(open("/tmp/mhw_masks.pkl","rb"))
B, T = D["B"], D["T"]          # (4071,60,60), (92,60,60)
masks = M["masks"]
nb, nlat, nlon = B.shape
nt = T.shape[0]

# 1) sea cells: finite on EVERY target day
sea = np.all(np.isfinite(T), axis=0)      # (60,60)
n_sea = int(sea.sum())
print("sea cells:", n_sea, "of", nlat*nlon)

cells = np.argwhere(sea)                  # (n_sea,2)
V = B[:, cells[:,0], cells[:,1]]          # (n_sea, 4071) float64
print("V shape:", V.shape, "finite frac in sea baseline:", float(np.isfinite(V).mean()))

def hazen90(P):
    """P: (n_cells, m) possibly NaN. Returns (n_cells,) hazen 90pct, NaN if no finite."""
    fin = np.isfinite(P)
    cnt = fin.sum(axis=1)
    out = np.full(P.shape[0], np.nan)
    ok = cnt > 0
    if not ok.any(): return out
    X = np.where(fin, P, np.inf)
    Xs = np.sort(X, axis=1)
    c = cnt[ok]
    h0 = 0.9*(c-1)
    j = np.floor(h0).astype(np.int64)
    frac = h0 - j
    idx = np.arange(P.shape[0])[ok]
    a = Xs[idx, j]
    b = Xs[idx, j+1]
    val = np.where(frac==0, a, a + frac*(b-a))
    out[ok] = val
    return out

def nanmean_rows(P):
    fin = np.isfinite(P)
    cnt = fin.sum(axis=1)
    out = np.full(P.shape[0], np.nan)
    ok = cnt > 0
    out[ok] = np.where(fin[ok], P[ok], 0.0).sum(axis=1) / cnt[ok]
    return out

Th = np.empty((n_sea, 366)); Cl = np.empty((n_sea, 366))
for d in range(1, 367):
    if d == 60: continue
    P = V[:, masks[d]]
    Th[:, d-1] = hazen90(P)
    Cl[:, d-1] = nanmean_rows(P)
# day 60 (index 59): mean of days 59 and 61 (indices 58, 60)
Th[:, 59] = (Th[:, 58] + Th[:, 60]) / 2.0
Cl[:, 59] = (Cl[:, 58] + Cl[:, 60]) / 2.0

nan_th = np.isnan(Th).any(axis=1); nan_cl = np.isnan(Cl).any(axis=1)
print("cells with any NaN threshold:", int(nan_th.sum()), " any NaN climatology:", int(nan_cl.sum()))
print("pool-finite min/max per doy check: min finite count over cells/doy ->")
# sanity: overall stats
print("Th range: %.2f .. %.2f K ; Cl range: %.2f .. %.2f K" % (np.nanmin(Th), np.nanmax(Th), np.nanmin(Cl), np.nanmax(Cl)))

# --- manual verification for one cell, one doy ---
import datetime as dt
Vcell = V[0]
d = 153  # Jun 1
Pman = Vcell[masks[d]]
x = np.sort(Pman[np.isfinite(Pman)])
n = len(x)
h0 = 0.9*(n-1); j = int(np.floor(h0)); g = h0-j
qman = x[j] + g*(x[j+1]-x[j]) if g>0 else x[j]
print("verify cell0 doy153: manual %.6f vs vectorized %.6f  (n=%d)" % (qman, Th[0,152], n))
cman = np.nanmean(Pman)
print("verify clim manual %.6f vs %.6f" % (cman, Cl[0,152]))

pickle.dump({"Th":Th,"Cl":Cl,"cells":cells,"sea":sea}, open("/tmp/mhw_thresh.pkl","wb"))
print("saved")