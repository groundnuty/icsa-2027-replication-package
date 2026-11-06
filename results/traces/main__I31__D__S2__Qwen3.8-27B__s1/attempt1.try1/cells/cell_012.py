import numpy as np, warnings
warnings.filterwarnings("ignore")
D = np.load('/work/region_data.npz'); F = np.load('/work/final_state.npz')
tgt = D['tgt']; t_tgt = F['t_tgt']
sea = F['sea']; doyt = F['doyt']

# recompute smoothed thresholds quickly (same pipeline)
base = D['base']; t_base = D['t_base']
cum = np.concatenate([[0], np.cumsum([31,29,31,30,31,30,31,31,30,31,30,31])])
def doy_of(strs):
    m = np.array([int(s[5:7]) for s in strs]); d = np.array([int(s[8:10]) for s in strs])
    return cum[m-1] + d
doyb = doy_of(t_base)
in_base = (t_base >= "1992-01-01") & (t_base <= "2002-12-31")
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
print("target median SST (degC) over Jun-Aug:", np.nanmedian(T-273.15))
print("threshold median (degC) over Jun-Aug: ", np.median(tht-273.15))
# daily median gap
gap = np.nanmedian(T-273.15, axis=1) - np.median(tht-273.15, axis=1)
print("daily median SST - median thr: min %.2f max %.2f" % (gap.min(), gap.max()))
hot = T >= tht
print("hot fraction:", hot.mean())
# longest raw hot runs (no 5-day filter)
lens = []
for c in range(sea.sum()):
    x = hot[:, c].astype(np.int8); p = np.concatenate([[0], x, [0]]); df = np.diff(p)
    s = np.where(df==1)[0]; e = np.where(df==-1)[0]
    if len(s): lens.append((e-s).max())
lens = np.array(lens)
print("longest raw hot run: overall max", lens.max(), "| per-cell max>=3:", (lens>=3).sum(), ">=4:", (lens>=4).sum())
