
import numpy as np, datetime
# test quantile implementations on a controlled array
x = np.arange(121, dtype=np.float64)
h = (121 + 1) * 0.9 - 1
print("h:", repr(h))
print("manual:", x[int(np.floor(h))] + (h - np.floor(h)) * (x[min(int(np.floor(h))+1, 120)] - x[int(np.floor(h))]))
print("numpy hazen:", np.quantile(x, 0.9, method='hazen'))
print("numpy linear:", np.quantile(x, 0.9, method='linear'))

# now real case
S_base = np.load('work/S_base.npy')
base_dates = [datetime.date(1992,1,1) + datetime.timedelta(days=i) for i in range(4018)]
win_dates = [datetime.date(1991,12,27) + datetime.timedelta(days=i) for i in range(4028)]
date2idx = {d: i for i, d in enumerate(win_dates)}
dbm = {1:0, 2:31, 3:60, 4:91, 5:121, 6:152, 7:182, 8:213, 9:244, 10:274, 11:305, 12:335}
def slow_pool(cell, doyear):
    vals = []
    for j, b in enumerate(base_dates):
        bdoy = dbm[b.month] + b.day
        if bdoy == doyear:
            for k in range(-5, 6):
                t = b + datetime.timedelta(days=k)
                vals.append(S_base[date2idx[t], cell[0], cell[1]])
    return np.array(vals, dtype=np.float64)
c = 2139; ci = np.unravel_index(c, (60,60))
X = slow_pool(ci, 153)
print("pool size:", X.size, "nfinite:", np.isfinite(X).sum())
xf = X[~np.isnan(X)]
srt = np.sort(xf)
n = srt.size
h = (n + 1) * 0.9 - 1
print("n:", n, "h:", repr(h))
print("sorted around idx 105-115:", srt[105:116])
lo = int(np.floor(h))
print("manual q:", srt[lo] + (h - lo) * (srt[min(lo+1, n-1)] - srt[lo]))
print("numpy nanquantile hazen:", np.nanquantile(X, 0.9, method='hazen'))
# pipeline raw threshold for this cell/doy
thr_raw = np.load('work/thr_raw.npy')
print("pipeline thr_raw[152, 2139]:", thr_raw[152, c])
