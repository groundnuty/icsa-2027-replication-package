import numpy as np, pickle, time
t0 = time.time()
data = np.load('/work/data.npy')
pools = pickle.load(open('/work/pools.pkl','rb'))
nH = 60*60
flat = data[:4028].reshape(4028, nH)

thr = np.empty((366, nH), dtype='float64')  # index k = doy k+1
clim = np.empty((366, nH), dtype='float64')
for d in range(1, 367):
    if d == 60:
        continue
    idxs = pools[d]
    vals = flat[idxs]
    thr[d-1] = np.quantile(vals, 0.9, axis=0, method='hazen')
    clim[d-1] = vals.mean(axis=0)
# day 60 (index 59) = mean of day 59 (index 58) and day 61 (index 60)
thr[59] = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])
print('quantiles done', round(time.time()-t0,1),'s')

ker = np.ones(31, dtype='float64') / 31.0
def circ_smooth(a):
    padded = np.concatenate([a[-15:], a, a[:15]], axis=0)
    return np.apply_along_axis(lambda m: np.convolve(m, ker, mode='valid'), 0, padded)

thr_s = circ_smooth(thr)
clim_s = circ_smooth(clim)
print('smoothing done', round(time.time()-t0,1),'s')
np.save('/work/thr_s.npy', thr_s)
np.save('/work/clim_s.npy', clim_s)

j = 25*60+25
for d in [153, 183, 213, 244]:
    print(f'doy {d}: thr={thr_s[d-1,j]:.4f} clim={clim_s[d-1,j]:.4f}')
# wrap check doy 1 (index 0): mean of indices 351..365 (doys 352..366) and 0..15 (doys 1..16)
manual = thr[np.r_[351:366, 0:16], j].mean()
print('wrap check doy1:', round(manual,6), round(thr_s[0,j],6))
# wrap check doy 352 (index 351): indices 336..365 and 0..5
manual3 = thr[np.r_[336:366, 0:6], j].mean()
print('wrap check doy352:', round(manual3,6), round(thr_s[351,j],6))
# non-wrap check doy 183 (index 182): indices 167..197
manual4 = thr[167:198, j].mean()
print('plain check doy183:', round(manual4,6), round(thr_s[182,j],6))
