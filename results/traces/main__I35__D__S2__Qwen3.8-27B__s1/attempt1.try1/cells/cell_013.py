import numpy as np, pickle
d = pickle.load(open('/work/step1.pkl','rb'))
S_ext, doy_ext, M, t_ext = d['S_ext'], d['doy_ext'], d['M'], d['t_ext']
S_ext_c = S_ext.reshape(-1, S_ext.shape[0])

# manual HF type-5 quantile for one cell, day 153 (June 1)
c = 0
i = 152  # 0-based
X = S_ext_c[c, np.flatnonzero(M[i])]
Xv = X[~np.isnan(X)]
n = len(Xv)
print('pool n:', n, 'of 121 (NaNs dropped:', 121-n, ')')
def hf5(x, q):
    x = np.sort(x); n = len(x)
    h = (np.arange(1, n+1) - 0.5)/n
    return float(np.interp(q, h, x))
print('manual hf5 q0.9:', hf5(Xv, 0.9))
print('np nanquantile hazen:', float(np.nanquantile(X, 0.9, method='hazen')))
# mean check
print('manual mean:', Xv.mean(), 'np nanmean:', float(np.nanmean(X)))
# pool date pattern for day 153: should be 11 windows May27-Jun6 in 1992..2002
cols = np.flatnonzero(M[i])
dd = t_ext[cols]
print('first/last:', str(dd[0])[:10], str(dd[-1])[:10])
import datetime as dt
print('window lengths per year:', [int((dd >= np.datetime64(f'{y}-05-27')).sum() - (dd >= np.datetime64(f'{y+1}-01-01')).sum()) for y in range(1992, 2003)])

# Also verify threshold array for that cell at day 153 equals pre-smoothing value
d2 = pickle.load(open('/work/step2.pkl','rb'))
thr_sm = d2['thr_sm']
# recompute raw thr for cell 0 day 153 quickly
print('cell0 thr_sm[152]:', thr_sm[c, 152])
# spot check: recompute smoothing for cell 0 day 152 by hand
cols_all = [np.flatnonzero(M[j]) for j in range(366)]
raw = np.array([np.nanquantile(S_ext_c[c, cols_all[j]], 0.9, method='hazen') if j != 59 else np.nan for j in range(366)])
raw[59] = 0.5*(raw[58] + raw[60])
win = [(152 + k) % 366 for k in range(-15, 16)]
print('manual smooth day153:', raw[win].mean())
