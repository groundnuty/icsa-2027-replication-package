import numpy as np, datetime as dt
W = '/work/work'
hot = np.load(f'{W}/hot.npy')
sea = np.load(f'{W}/sea.npy')
tgt = np.load(f'{W}/target_data.npy').astype(np.float64)
thr = np.load(f'{W}/thr.npy')
tdates = [dt.date.fromisoformat(str(x)) for x in np.load(f'{W}/target_dates.npy')]

def runs_of_true(mask_1d):
    out = []; n = len(mask_1d); i = 0
    while i < n:
        if mask_1d[i]:
            j = i
            while j + 1 < n and mask_1d[j + 1]: j += 1
            out.append((i, j)); i = j + 1
        else:
            i += 1
    return out

# distribution of hot run lengths
from collections import Counter
L = Counter()
for y, x in zip(*np.where(sea)):
    for (a, b) in runs_of_true(hot[:, y, x]):
        L[b - a + 1] += 1
print('hot run-length distribution:', dict(sorted(L.items())))

# sample cell series
ys, xs = np.where(sea)
y0, x0 = ys[0], xs[0]
print('\nsample cell', y0, x0)
for i in range(92):
    sst = tgt[i, y0, x0]
    # threshold slot for this date
    d = tdates[i]
    k = d.timetuple().tm_yday
    kk = k if dt.date(d.year,12,31).timetuple().tm_yday == 366 else (k if k <= 59 else k+1)
    print(tdates[i], f'SST {sst:8.3f}  thr {thr[kk-1, y0, x0]:8.3f}  hot {sst >= thr[kk-1, y0, x0]}')
