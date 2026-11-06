import numpy as np, datetime as dt
A = np.load('analysis.npz')
hot = A['hot']; mhw = A['mhw']; sea = A['sea']; thr = A['thr']
St = np.load('St.npy'); tgt_dates = np.load('tgt_dates.npy')
lat = np.load('lat.npy'); lon = np.load('lon.npy')
doy_t = A['doy_t']

# NaN pattern in target
print('NaN per target day: uniq', np.unique(np.isnan(St).sum(axis=(1,2))))
# hot counts per day around event 1
print('hot/day t20..t40:', [int(hot[k].sum()) for k in range(20, 41)])
print('hot/day t60..t74:', [int(hot[k].sum()) for k in range(60, 75)])
print('mhw cell-days total:', int(mhw.sum()), ' hot cell-days:', int(hot.sum()))

# regional mean SST vs mean threshold (sea cells)
sst_reg = np.nanmean(np.where(sea, St, np.nan), axis=(1,2))
thr_reg = np.nanmean(np.where(sea, thr[doy_t-1], np.nan), axis=(1,2))
for k in list(range(20,40)):
    print('t%02d %s SST %7.3f thr %7.3f diff %+6.3f' % (k, str(tgt_dates[k])[:10], sst_reg[k], thr_reg[k], sst_reg[k]-thr_reg[k]))
