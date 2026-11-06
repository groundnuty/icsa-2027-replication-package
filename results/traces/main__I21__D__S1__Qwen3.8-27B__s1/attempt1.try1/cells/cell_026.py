import numpy as np, datetime
z = np.load('/work/region.npz'); s = np.load('/work/doy_stats.npz')
base_dates = [datetime.date.fromisoformat(x) for x in z['base_dates']]
base_sst = z['base_sst']; st = s['sm_thresh']; rc = s['raw_clim']
tgt_doy = s['target_doy']

# 1) verify pool dates for d=153 (Jun 1): should be May27-Jun6 of each baseline year
CUM = [0,31,60,91,121,152,182,213,244,274,305,335]
doy = np.array([CUM[d.month-1]+d.day for d in base_dates])
is_anchor = np.zeros(len(base_dates), bool); is_anchor[5:-5] = True
centers = np.where(is_anchor & (doy == 153))[0]
dates_pool = sorted(base_dates[c+k] for c in centers for k in range(-5,6))
print("d153 pool dates per year:", [str(d) for d in dates_pool[:12]], "... total:", len(dates_pool))

# 2) independent hazen quantile & mean for one sea cell, d=153
finite_all = np.all(np.isfinite(s['raw_thresh']), axis=0)
col = int(np.where(finite_all)[0][3])
pool = base_sst[[c+k for c in centers for k in range(-5,6) if c+k>=0], 0, 0]  # wrong shape guard
# base_sst is (4028,60,60); col is flattened index -> r,cc
r, cc = divmod(col, 60)
idx = np.concatenate([np.arange(c-5, c+6) for c in centers])
vals = base_sst[idx, r, cc].astype(np.float64)
vals_f = vals[np.isfinite(vals)]
def hazen(q, p):
    x = np.sort(q); n = len(x)
    h = n*p + 0.5          # 1-based
    k = np.floor(h); g = h - k
    if k >= n: return x[-1]
    if k == 0: return x[0] if g == 0 else x[0] + (x[1]-x[0])*g
    return x[k-1] + (x[k]-x[k-1])*g
print("manual hazen thr:", hazen(vals_f, 0.9), "raw stored:", s['raw_thresh'][152, col])
print("manual mean:", vals_f.mean(), "raw stored clim:", rc[152, col])
# compare numpy nanquantile
print("np nanquantile hazen:", np.nanquantile(vals, 0.9, method='hazen'))
# sanity: thresholds should be >= climatology-ish and below max SST
tgt = z['tgt_sst']
d = tgt_doy[0]
print("cell col", col, "tgt day0:", tgt[0, r, cc], "thr smoothed:", st[d-1, col], ">= ?", tgt[0,r,cc] >= st[d-1, col])
print("sm thr at target doys, this cell:", st[152:158, col].round(4))
