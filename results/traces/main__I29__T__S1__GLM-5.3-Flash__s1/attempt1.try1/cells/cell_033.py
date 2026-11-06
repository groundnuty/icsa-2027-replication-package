import numpy as np, datetime

tgt = np.load('target.npy').astype(np.float64)   # (92,60,60), float32 values exactly represented
thresh = np.load('thresh.npy')                    # (366,60,60)
start = datetime.date(2015,6,1)
dates = [start + datetime.timedelta(days=k) for k in range(92)]

# day-of-year map (1..366, non-leap 2015 skips 60)
def doy_of(d):
    y = d.timetuple().tm_yday
    leap = (d.year%4==0 and d.year%100!=0) or (d.year%400==0)
    return y if leap or y < 60 else y+1
tdoy = np.array([doy_of(d) for d in dates])
print('target doys:', tdoy[0], '...', tdoy[-1], '| contains 60?', 60 in tdoy.tolist())

# 1) sea cells: finite SST on every day of target period
finite = np.isfinite(tgt)          # (92,60,60)
per_cell_all_finite = finite.all(axis=0)
n_landish = (~per_cell_all_finite).sum()
print('cells NOT finite on all target days:', n_landish, '=> sea cells:', per_cell_all_finite.sum())
# breakdown: all-NaN vs partial
allnan = np.isfinite(tgt).sum(axis=0)==0
print('all-NaN cells:', allnan.sum(), '| partial-NaN cells:', (n_landish - allnan.sum()))
# which doys have NaN at sea cells?
nan_days = np.where((~finite).any(axis=(1,2)))[0]
print('days with any NaN in region:', [str(dates[i]) for i in nan_days][:10], 'count', len(nan_days))

# 2) hot days: SST >= threshold for that day of year
th = thresh[tdoy-1]                # (92,60,60)
hot = tgt >= th                    # float64 comparison; NaN >= x -> False
print('hot days count:', hot.sum(), 'of', hot.size)
np.save('hot.npy', hot); np.save('per_cell_all_finite.npy', per_cell_all_finite)
