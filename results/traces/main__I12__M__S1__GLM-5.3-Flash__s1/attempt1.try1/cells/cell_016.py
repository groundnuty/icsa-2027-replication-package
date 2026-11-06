import numpy as np, warnings, pickle
dates = np.load('/tmp/dates.npy')
data = np.load('/tmp/sst_needed.npy')
n_base = 4028
base_dates = dates[:n_base]

md_doy = {}
cum = [0,31,59,90,120,151,181,212,243,273,304,334]
for m in range(1,13):
    for day in range(1,32):
        if not (m==2 and day>29) and not (m in (4,6,9,11) and day>30):
            md_doy[(m,day)] = cum[m-1] + day
md_doy[(2,29)] = 60
base_doy = np.array([md_doy[(int(str(d)[5:7]), int(str(d)[8:10]))] for d in base_dates])

clim = np.empty((366, 60, 60), dtype='float64')
thresh = np.empty((366, 60, 60), dtype='float64')
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    for d in range(1, 367):
        idx = np.where(np.abs(base_doy.astype(int) - d) <= 5)[0]
        pool = data[idx].astype('float64')          # (n_i, 60, 60)
        clim[d-1] = np.nanmean(pool, axis=0)
        thresh[d-1] = np.nanquantile(pool, 0.9, axis=0, method='hazen')
print('raw arrays done')
# day 60 <- mean of day 59 and 61
clim[59] = 0.5*(clim[58] + clim[60])
thresh[59] = 0.5*(thresh[58] + thresh[60])
# 31-day centred moving mean, circular over 366
w = 15
def circ_smooth(a):
    ext = np.concatenate([a[-w:], a, a[:w]], axis=0)   # (396, 60, 60)
    kernel = np.ones(31)/31.0
    return np.apply_along_axis(lambda m: np.convolve(m, kernel, mode='valid'), 0, ext)
clim_s = circ_smooth(clim)
thr_s  = circ_smooth(thresh)
print('smoothed. shapes', clim_s.shape, thr_s.shape)
# quick sanity: values plausible
print('clim range', np.nanmin(clim_s).round(3), np.nanmax(clim_s).round(3))
print('thr range', np.nanmin(thr_s).round(3), np.nanmax(thr_s).round(3))
np.save('/tmp/clim_smooth.npy', clim_s)
np.save('/tmp/thr_smooth.npy', thr_s)
np.save('/tmp/clim_raw.npy', clim)
np.save('/tmp/thr_raw.npy', thresh)
print('saved')
