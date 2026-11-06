
import numpy as np, pickle, time
t0 = time.time()
S_base = np.load('/work/work/S_base.npy')
S_t    = np.load('/work/work/S_t.npy')
with open('/work/work/pool_idx.pkl','rb') as f: pool_idx = pickle.load(f)
with open('/work/work/dates.pkl','rb') as f: D = pickle.load(f)
base_dates, target_dates, sea = D['base'], D['target'], D['sea']
ml = [31,29,31,30,31,30,31,31,30,31,30,31]
leap_cum = np.zeros(13, int)
for m in range(12): leap_cum[m+1] = leap_cum[m] + ml[m]
def doy(dt): return int(leap_cum[dt.month-1] + dt.day)

cells = sea  # (n,2)
n = cells.shape[0]
print("sea cells:", n)

TH = np.empty((366, n)); CL = np.empty((366, n))
pool_sizes = {}
for d in range(1, 367):
    if d == 60: continue
    idx = pool_idx[d]
    vals = S_base[idx][:, cells[:,0], cells[:,1]]   # (L, n)
    pool_sizes[d] = int(np.isfinite(vals).sum(axis=0).min())
    TH[d-1] = np.nanquantile(vals, 0.9, axis=0, method='hazen')
    CL[d-1] = np.nanmean(vals, axis=0)

# any non-finite results?
print("non-finite TH cols (any doy):", int(np.isnan(TH).sum()), "CL:", int(np.isnan(CL).sum()))
print("min pool finite count across all cells/doys:", min(pool_sizes.values()))
print("pool size doy1:", pool_sizes[1], "doy153:", pool_sizes[153])

# day 60 = mean of 59 and 61
TH[59] = 0.5*(TH[58] + TH[60])
CL[59] = 0.5*(CL[58] + CL[60])

# smoothing: centred 31-day moving mean, wrapping over 366
off = (np.arange(366)[:,None] + np.arange(-15,16)[None,:]) % 366
TH_s = TH[off].mean(axis=1)
CL_s = CL[off].mean(axis=1)

# sanity: compare one cell's doy-153 threshold against manual computation
c = 0
i, j = cells[c]
d = 153
vals = S_base[pool_idx[d], i, j]
vals = vals[np.isfinite(vals)]
man = np.quantile(vals, 0.9, method='hazen')
manm = vals.mean()
print("manual vs vectorised (cell0, doy153):", man, TH[d-1, c], "match:", np.isclose(man, TH[d-1,c]))
print("manual mean:", manm, "CL:", CL[d-1, c], "match:", np.isclose(manm, CL[d-1,c]))
print("smoothing check doy153 cell0 (manual):", np.mean(TH[(np.arange(153-15,153+16)) % 366, c]), "TH_s:", TH_s[152, c])
print("TH range:", TH_s.min(), TH_s.max(), " CL range:", CL_s.min(), CL_s.max())
print("doy60 interpolation check:", np.allclose(TH[59], 0.5*(TH[58]+TH[60])))

np.save('/work/work/TH_s.npy', TH_s)
np.save('/work/work/CL_s.npy', CL_s)
np.save('/work/work/TH_raw.npy', TH)
print("done", round(time.time()-t0,1))
