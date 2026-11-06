import numpy as np
thr = np.load('/work/thr_s.npy')  # smoothed? no - thr_s is smoothed; recompute raw for check
# load raw by re-deriving from saved smoothed only - instead verify with raw from pools quickly for one cell
import pickle, datetime as dt
data = np.load('/work/data.npy')
pools = pickle.load(open('/work/pools.pkl','rb'))
nH = 60*60
flat = data[:4028].reshape(4028, nH)
j = 25*60+25
raw = np.empty(366)
for d in range(1,367):
    if d == 60: continue
    raw[d-1] = np.quantile(flat[pools[d]][:, j], 0.9, method='hazen')
raw[59] = 0.5*(raw[58]+raw[60])
# doy 352 (index 351): window = indices 336..365 (doys 337..366) + index 0 (doy 1)
manual = raw[np.r_[336:366, [0]]].mean()
thr_s = np.load('/work/thr_s.npy')
print('doy352 check:', round(manual,6), round(thr_s[351,j],6))
# doy 60 (index 59): window = indices 44..74 (doys 45..75)
manual2 = raw[44:75].mean()
print('doy60 check:', round(manual2,6), round(thr_s[59,j],6))
