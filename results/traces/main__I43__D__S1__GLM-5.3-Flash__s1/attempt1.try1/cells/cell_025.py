import numpy as np, pickle, time
t0 = time.time()
data = np.load('/work/data.npy')
pools = pickle.load(open('/work/pools.pkl','rb'))
nH = 60*60
flat = data[:4028].reshape(4028, nH)

thr = np.empty((366, nH), dtype='float64')
clim = np.empty((366, nH), dtype='float64')
for d in range(1, 367):
    if d == 60:
        continue
    idxs = pools[d]
    vals = flat[idxs]
    thr[d] = np.quantile(vals, 0.9, axis=0, method='hazen')
    clim[d] = vals.mean(axis=0)
thr[60] = 0.5*(thr[59] + thr[61])
clim[60] = 0.5*(clim[59] + clim[61])
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
# wrap check for doy 1 (index 0): mean of doys 352..366 and 1..16 -> indices 351..365, 0..15
manual = thr[list(range(351,366))+list(range(0,16)), j].mean()
print('wrap check doy1:', round(manual,6), round(thr_s[0,j],6))
manual2 = thr[list(range(229,244))+list(range(0,16)), j].mean()  # doy 244+16 wraps: doys 229..366? 
# proper: doy 244 (index243) averages indices 228..258; doy 352 (index351) averages 336..365 + 0..5
manual3 = thr[np.r_[336:366, 0:6], j].mean()
print('wrap check doy352:', round(manual3,6), round(thr_s[351,j],6))
