import numpy as np, pandas as pd, pickle, warnings

with open('/tmp/stepA.pkl','rb') as fh: A1 = pickle.load(fh)
with open('/tmp/stepA2.pkl','rb') as fh: A2 = pickle.load(fh)
bdates = A1['bdates']; arr_sea = A1['arr_sea']
m_start = np.array([1,32,61,92,122,153,183,214,245,275,306,336])
bdoy = m_start[bdates.month.values-1] + bdates.day.values - 1

# Version W pools (window on remapped doy)
def pool_sel_W(d):
    return np.isin(bdoy, np.array(sorted({((d + k - 1) % 366) + 1 for k in range(-5, 6)})))
# Version E pools (exact calendar shifts)
mem = A2['mem']

raw_W = np.full((366, arr_sea.shape[1]), np.nan)
raw_E = np.full((366, arr_sea.shape[1]), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for d in range(1, 367):
        if d == 60: continue
        raw_W[d-1] = np.nanquantile(arr_sea[pool_sel_W(d)], 0.9, axis=0, method='hazen')
        raw_E[d-1] = np.nanquantile(arr_sea[mem[:, d-1]], 0.9, axis=0, method='hazen')
d_raw = np.abs(raw_E - raw_W).max(axis=1)
bad_raw = np.where(d_raw > 1e-9)[0] + 1
print("raw threshold differs at doys:", bad_raw.tolist())
print("pool membership counts differ at doys:", [d for d in range(1,367) if d != 60 and (pool_sel_W(d).sum() != mem[:, d-1].sum())])

d_s = np.abs(A2['thresh_s'] - A1['thresh_s']).max(axis=1)
bad_s = np.where(d_s > 1e-9)[0] + 1
print("smoothed threshold differs at doys:", bad_s.tolist())
d_sc = np.abs(A2['clim_s'] - A1['clim_s']).max(axis=1)
print("smoothed clim max delta:", d_sc.max())
print("earlier-reported doy 351 delta:", d_s[350], "| global max smoothed delta:", d_s.max())
