import numpy as np, warnings
warnings.filterwarnings("ignore")
D = np.load('/work/region_data.npz'); F = np.load('/work/final_state.npz')
tgt = D['tgt']; t_tgt = F['t_tgt']; t_base = D['t_base']; base = D['base']
sea = F['sea']; doyt = F['doyt']
ns = int(sea.sum())

cum = np.concatenate([[0], np.cumsum([31,29,31,30,31,30,31,31,30,31,30,31])])
def doy_of(strs):
    m = np.array([int(s[5:7]) for s in strs]); d = np.array([int(s[8:10]) for s in strs])
    return cum[m-1] + d
doyb = doy_of(t_base)
in_base = (t_base >= "1992-01-01") & (t_base <= "2002-12-31")

# independent per-cell check for one cell: cell 0 (lat 58.7, lon 18.7)
c = 0
col = base[:, :, 0, 0]  # wait base is (4028, 60, 60); cell (0,0)
col = base[:, 0, 0]
doy = doyt[0]  # 153 (June 1)
idx = np.where((doyb == doy) & in_base)[0]
pool = np.concatenate([base[i-5:i+6, 0, 0] for i in idx])
pool = pool[~np.isnan(pool)]
print("cell(0,0) pool n:", len(pool))
srt = np.sort(pool)
# manual hazen: h=(n+1)p (1-based)
h = (len(pool)+1)*0.9
i0 = int(np.floor(h)) - 1
frac = h - np.floor(h)
q_manual = srt[i0] + frac*(srt[i0+1]-srt[i0])
q_np = np.nanquantile(pool, 0.9, method='hazen')
print("manual hazen: %.6f  numpy: %.6f  diff: %.2e" % (q_manual, q_np, abs(q_manual-q_np)))
print("pool min/med/max (degC): %.2f %.2f %.2f" % (pool.min()-273.15, np.median(pool)-273.15, pool.max()-273.15))

# margin analysis over target
thr = np.full((366, 3600), np.nan)
for dd in range(1, 367):
    if dd == 60: continue
    idx = np.where((doyb == dd) & in_base)[0]
    pool = np.concatenate([base[i-5:i+6] for i in idx]).reshape(121, 3600)
    thr[dd-1] = np.nanquantile(pool, 0.90, axis=0, method='hazen')
thr[59] = (thr[58] + thr[60]) / 2.0
def smooth366(a):
    pad = np.concatenate([a[-15:], a, a[:15]])
    from numpy.lib.stride_tricks import sliding_window_view
    return sliding_window_view(pad, 31, axis=0).mean(axis=-1)
thr_s = smooth366(thr)

T = tgt.reshape(92, 3600)[:, sea]
tht = thr_s[doyt-1][:, sea]
margin = T - tht   # >=0 => hot
print("\nmargin SST-thr over target: max overall %.3f K (%.3f degC)" % (margin.max(), margin.max()-0))
top = np.argsort(margin.ravel())[-10:][::-1]
for k in top:
    i, c = np.unravel_index(k, margin.shape)
    print("  %s cell(%d,%d) SST %.2f degC  thr %.2f degC  margin +%.3f" % (
        t_tgt[i], *np.unravel_index(c, (60,60)), T[i,c]-273.15, tht[i,c]-273.15, margin[i,c]))

# fraction of pool values >= threshold per cell-day (should be ~10%)
# check on June 1 pool for all cells
idx = np.where((doyb == 153) & in_base)[0]
pool = np.concatenate([base[i-5:i+6] for i in idx]).reshape(121, 3600)
q = thr[152]
frac = (np.nan_to_num(pool, nan=-np.inf) >= q[:, None]).sum(axis=0) / 121.0
print("\nJune-1 pool fraction >= q90: min %.3f med %.3f max %.3f" % (frac.min(), np.median(frac), frac.max()))
# warmest year check: max pool value per cell vs threshold
print("pool max (degC) med: %.2f ; thr (degC) med: %.2f" % (np.nanmax(pool,axis=0).median()-273.15, np.median(q)-273.15))
