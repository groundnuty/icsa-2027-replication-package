import numpy as np, datetime as dt
Sb = np.load('Sb.npy'); St = np.load('St.npy')
base_dates = np.load('base_dates.npy'); tgt_dates = np.load('tgt_dates.npy')
A = np.load('analysis.npz')
thr_raw = A['thr_raw']; thr = A['thr']

CUM = [0,31,60,91,121,152,182,213,244,274,305,335]
def doy_of(d): return CUM[d.month-1] + d.day

k0 = int(np.where(base_dates == np.datetime64('1992-01-01'))[0][0])
k1 = int(np.where(base_dates == np.datetime64('2002-12-31'))[0][0])
doy_base = np.array([doy_of(dt.date.fromisoformat(str(base_dates[k])[:10])) for k in range(k0, k1+1)])

d = 200  # 19 July
ks = np.where(doy_base == d)[0] + k0
print('n dates for doy 200:', ks.size)
print('dates:', [str(base_dates[k])[:10] for k in ks[:12]])
idx = np.unique((ks[:, None] + np.arange(-5, 6)[None, :]).ravel())
print('pool date span per year sample:', [str(base_dates[k])[:10] for k in idx[:13]])
pool = Sb[idx]
cell = (30, 30)
pv = pool[:, cell[0], cell[1]]
print('pool cell stats: n=%d finite=%d mean=%.3f  q90(hazen)=%.3f' % (pv.size, np.isfinite(pv).sum(), np.nanmean(pv), np.nanquantile(pv, 0.9, method='hazen')))
print('thr_raw[doy200, cell] =', thr_raw[199, cell[0], cell[1]])
print('Sb mid-July values cell:', np.nanmean(Sb[(base_dates >= np.datetime64('1995-07-14')) & (base_dates <= np.datetime64('1995-07-24')), cell[0], cell[1]]))
# target SST at that cell for comparison
print('St July cell mean:', np.nanmean(St[30:60, cell[0], cell[1]]))
# where is max thr? which DOY?
imax = np.unravel_index(np.nanargmax(thr), thr.shape)
print('max thr at doy', imax[0]+1, 'value', thr[imax], '  thr_raw at that doy:', np.nanmax(thr_raw[imax[0]]))
imin = np.unravel_index(np.nanargmin(thr), thr.shape)
print('min thr at doy', imin[0]+1, 'value', thr[imin])
# print raw threshold seasonal cycle for one sea cell
c = (30, 30)
print('thr_raw doy 1,59,61,100,152,153,183,213,244,274,305,335,365,366:')
for dd in [1,59,61,100,152,153,183,213,244,274,305,335,365,366]:
    print('  doy %3d: raw %8.3f  smoothed %8.3f' % (dd, thr_raw[dd-1, c[0], c[1]], thr[dd-1, c[0], c[1]]))
