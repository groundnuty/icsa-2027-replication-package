import numpy as np, warnings
warnings.filterwarnings("ignore")
D = np.load('/work/region_data.npz'); F = np.load('/work/final_state.npz')
tgt = D['tgt']; t_tgt = F['t_tgt']; t_base = D['t_base']; base = D['base']
sea = F['sea']; doyt = F['doyt']
T = tgt.reshape(92, 3600)[:, sea]
Tb = base.reshape(4028, 3600)[:, sea]
yr = np.array([int(s[:4]) for s in t_base])

cum = np.concatenate([[0], np.cumsum([31,29,31,30,31,30,31,31,30,31,30,31])])
def doy_of(strs):
    m = np.array([int(s[5:7]) for s in strs]); d = np.array([int(s[8:10]) for s in strs])
    return cum[m-1] + d
doyb = doy_of(t_base)
in_base = (t_base >= "1992-01-01") & (t_base <= "2002-12-31")

# per-year Jun-Aug median SST (sea cells), 1992-2002 and 2017
print("year : Jun-Aug median-cell SST (degC)")
for y in list(range(1992, 2003)):
    m = (yr == y) & (t_base >= f"{y}-06-01") & (t_base <= f"{y}-08-31")
    print(y, " : %.2f" % np.nanmedian(Tb[m]-273.15))
print("2017  : %.2f" % np.nanmedian(T-273.15))

# daily curves: doy 153 (Jun1), 183 (Jun31), 213 (Jul31), 243 (Aug31)
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

print("\ndoy  date   base-median  thr-median  2017-median  (degC)")
for doy in [153, 183, 213, 243]:
    # baseline daily median: mean over years of the doy median (fixed doy)
    m = (doyb == doy) & in_base
    bm = np.nanmedian(Tb[m] - 273.15, axis=1).mean()
    tm = np.median(thr_s[doy-1][:, sea] - 273.15)
    i = int(np.where(doyt == doy)[0][0])
    c2 = np.nanmedian(T[i] - 273.15)
    print("%3d  %s  %9.2f  %9.2f  %10.2f" % (doy, t_tgt[i], bm, tm, c2))

# robustness: longest hot runs under 4 quantile variants
def thr_variant(qfunc):
    th = np.full((366, 3600), np.nan)
    for dd in range(1, 367):
        if dd == 60: continue
        idx = np.where((doyb == dd) & in_base)[0]
        pool = np.concatenate([base[i-5:i+6] for i in idx]).reshape(121, 3600)
        th[dd-1] = qfunc(pool)
    th[59] = (th[58] + th[60]) / 2.0
    return smooth366(th)

def longest_runs(mask):
    L = 0
    for c in range(mask.shape[1]):
        x = mask[:, c].astype(np.int8); p = np.concatenate([[0], x, [0]]); df = np.diff(p)
        s = np.where(df==1)[0]; e = np.where(df==-1)[0]
        if len(s): L = max(L, int((e-s).max()))
    return L

def q_hazen(p): return np.nanquantile(p, 0.9, axis=0, method='hazen')
def q_type7(p): return np.nanquantile(p, 0.9, axis=0, method='linear')
def q_a(p):  # h1 = (n+1)p
    s = np.nan_to_num(p, nan=np.inf)
    # manual: per column
    out = np.empty(p.shape[1])
    for j in range(p.shape[1]):
        v = p[:, j]; v = v[~np.isnan(v)]; v = np.sort(v); n = len(v)
        h = (n+1)*0.9; i = int(np.floor(h)); f = h-i
        out[j] = v[i-1] + f*(v[i]-v[i-1]) if i < n else v[-1]
    return out
variants = {
  "hazen(numpy)": q_hazen,
  "linear/type7 (MATLAB default)": q_type7,
  "h1=(n+1)p": q_a,
}
for name, f in variants.items():
    ts = thr_variant(f)
    hot = T >= ts[doyt-1][:, sea]
    print("%-30s longest raw hot run = %d, hot frac = %.5f" % (name, longest_runs(hot), hot.mean()))
