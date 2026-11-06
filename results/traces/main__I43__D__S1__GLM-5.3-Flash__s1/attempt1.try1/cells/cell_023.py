import numpy as np, pickle, time
t0 = time.time()
data = np.load('/work/data.npy')
pools = pickle.load(open('/work/pools.pkl','rb'))

nH = 60*60
flat = data.reshape(4028, nH)   # baseline-window part

thr = np.empty((366, nH), dtype='float64')
clim = np.empty((366, nH), dtype='float64')
for d in range(1, 367):
    if d == 60:
        continue
    idxs = pools[d]
    vals = flat[idxs]                # (121, nH)
    thr[d] = np.quantile(vals, 0.9, axis=0, method='hazen')
    clim[d] = vals.mean(axis=0)

# day 60 = mean of day 59 and day 61
thr[60] = 0.5*(thr[59] + thr[61])
clim[60] = 0.5*(clim[59] + clim[61])

# --- circular 31-day centred moving mean (wrap over 366)
ker = np.ones(31, dtype='float64') / 31.0
def circ_smooth(a):
    # a: (366, nH); doy index 0..365 = day 1..366
    padded = np.concatenate([a[-15:], a, a[:15]], axis=0)
    out = np.apply_along_axis(lambda m: np.convolve(m, ker, mode='valid'), 0, padded)
    return out

t1 = time.time()
thr_s = circ_smooth(thr)
print('thr smoothing done', round(time.time()-t1,1),'s')
t1 = time.time()
clim_s = circ_smooth(clim)
print('clim smoothing done', round(time.time()-t1,1),'s')
print('total stats time', round(time.time()-t0,1),'s')
np.save('/work/thr_s.npy', thr_s)
np.save('/work/clim_s.npy', clim_s)

# quick check: values around summer for a central sea cell (row 25, col 25 -> flat 25*60+25)
j = 25*60+25
for d in [153, 183, 213, 244]:
    print(f'doy {d}: thr={thr_s[d-1,j]:.4f} clim={clim_s[d-1,j]:.4f}')
