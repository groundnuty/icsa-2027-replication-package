import numpy as np, pickle, time, json, datetime as dt
t0 = time.time()
data = np.load('/work/data.npy')
print('data shape', data.shape)
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

thr_s = circ_smooth(thr); print('thr smoothing done', round(time.time()-t0,1),'s')
clim_s = circ_smooth(clim); print('clim smoothing done', round(time.time()-t0,1),'s')
np.save('/work/thr_s.npy', thr_s)
np.save('/work/clim_s.npy', clim_s)

j = 25*60+25
for d in [153, 183, 213, 244]:
    print(f'doy {d}: thr={thr_s[d-1,j]:.4f} clim={clim_s[d-1,j]:.4f}')
# also check smoothing wrap correctness manually for doy 1 (=index0): mean of doys 352..366,1..16
manual = thr[list(range(352,367))+list(range(1,17)), j].mean()
print('wrap check doy1:', manual, thr_s[0, j])
