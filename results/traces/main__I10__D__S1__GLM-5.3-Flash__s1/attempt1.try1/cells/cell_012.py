import numpy as np, datetime as dt, warnings
warnings.filterwarnings('ignore')
CUM = [0,31,60,91,121,152,182,213,244,274,305,335]
def mdoy(y,m,d): return CUM[m-1]+d

thr = np.load('/work/thr_raw.npy'); clim = np.load('/work/clim_raw.npy')
T = np.load('/work/target_sst.npy'); tstr = np.load('/work/target_datestr.npy')

def smooth31(a):
    p = np.concatenate([a[-15:], a, a[:15]], axis=0)   # p[k] = a[(k-15) mod 366]
    c = np.cumsum(p, axis=0)
    s = c[30:].copy()                                   # s[0]=c[30]=sum p[0..30]
    s[1:] = c[31:] - c[:-31]                            # s[j]=sum p[j..j+30]
    return s/31.0
thr_s = smooth31(thr); clim_s = smooth31(clim)

# brute-force verification for a few days and cells
rng = np.random.default_rng(0)
cells = [(r,c) for r in rng.integers(0,60,4) for c in rng.integers(0,60,4)]
ok = True
for j in [0, 1, 59, 152, 243, 365]:
    idxs = [(j-15+k) % 366 for k in range(31)]
    ref_t = thr[idxs].mean(axis=0); ref_c = clim[idxs].mean(axis=0)
    ok &= np.allclose(thr_s[j], ref_t) and np.allclose(clim_s[j], ref_c)
print('smooth31 vs brute force (6 days, 16 cells):', bool(ok))
# explicit wrap check day 366
chk366 = np.concatenate([thr[350:], thr[:15]]).mean(axis=0)   # days 351..366,1..15
print('day366 window == days351..366,1..15:', np.allclose(thr_s[365], chk366))
np.save('/work/thr_s.npy', thr_s); np.save('/work/clim_s.npy', clim_s)

sea = np.isfinite(T).all(axis=0)
print('sea cells:', int(sea.sum()))
print('sea-cell baseline NaN days max:', int(np.isnan(np.load('/work/baseline_sst.npy')[:,sea]).sum(axis=0).max()))
print('NaNs in thr_s/clim_s on sea cells:', int(np.isnan(thr_s[:,sea]).sum()), int(np.isnan(clim_s[:,sea]).sum()))

tdoy = np.array([mdoy(int(s[:4]),int(s[4:6]),int(s[6:])) for s in tstr])
print('target doys:', tdoy[0], '->', tdoy[-1], 'contig:', bool(np.all(np.diff(tdoy)==1)))
hot = np.zeros(T.shape, bool)
for t in range(T.shape[0]):
    hot[t] = T[t] >= thr_s[tdoy[t]-1]
np.save('/work/hot.npy', hot); np.save('/work/sea.npy', sea)
print('hot day-cells (sea):', int(hot[:,sea].sum()), '=', round(hot[:,sea].sum()/(sea.sum()*92)*100,2), '%')
print('sample cell (30,30): sea', bool(sea[30,30]), 'T Jun1-5:', T[:5,30,30].round(2),
      'thr d153-157:', thr_s[152:157,30,30].round(2), 'clim:', clim_s[152:157,30,30].round(2))
