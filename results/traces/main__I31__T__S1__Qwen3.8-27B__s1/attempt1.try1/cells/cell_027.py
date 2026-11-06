
import numpy as np, datetime

S_base = np.load('work/S_base.npy')
thr_raw_pipe = np.load('work/thr_raw.npy')
clim_raw_pipe = np.load('work/clim_raw.npy')
thr_s_pipe = np.load('work/thr_smooth.npy')
N = 3600

dbm = {1:0, 2:31, 3:60, 4:91, 5:121, 6:152, 7:182, 8:213, 9:244, 10:274, 11:305, 12:335}
mdays = {1:31,2:29,3:31,4:30,5:31,6:30,7:31,8:31,9:30,10:31,11:30,12:31}
doy2md = {}
for m in range(1, 13):
    for dd in range(1, mdays[m] + 1):
        doy2md[dbm[m] + dd] = (m, dd)

win_start = datetime.date(1991,12,27)
widx = {win_start + datetime.timedelta(days=i): i for i in range(4028)}

def type5_quantile(x, p=0.9):
    x = np.sort(x[~np.isnan(x)]); n = x.size
    if n == 0: return np.nan
    h1 = n * p + 0.5
    lo1 = int(np.floor(h1))
    if lo1 >= n: return x[-1]
    frac = h1 - lo1
    return x[lo1-1] + frac * (x[lo1] - x[lo1-1])

need = list(range(138, 260))
maxdiff_q = 0.0; maxdiff_m = 0.0
for d in need:
    m, dd = doy2md[d]
    vals = np.empty((11, 11, N))
    for yi, Y in enumerate(range(1992, 2003)):
        b = datetime.date(Y, m, dd)
        for k in range(-5, 6):
            t = b + datetime.timedelta(days=k)
            vals[yi, k + 5, :] = S_base[widx[t]].reshape(N)
    X = vals.reshape(121, N).astype(np.float64)
    q = np.empty(N); mu = np.empty(N)
    for c in range(N):
        q[c] = type5_quantile(X[:, c])
        f = X[:, c][~np.isnan(X[:, c])]
        mu[c] = f.mean() if f.size else np.nan
    dq = float(np.nanmax(np.abs(q - thr_raw_pipe[d-1]))); dm = float(np.nanmax(np.abs(mu - clim_raw_pipe[d-1])))
    maxdiff_q = max(maxdiff_q, dq); maxdiff_m = max(maxdiff_m, dm)
    if d in (138, 153, 197, 244, 259):
        print(f"doy {d}: max|q diff|={dq:.3e} max|mean diff|={dm:.3e}")
print("GLOBAL max diff quantile:", maxdiff_q, " mean:", maxdiff_m)

def circ31_ref(a, d):
    win = [a[(d + k - 1) % 366] for k in range(-15, 16)]
    return np.mean(np.stack(win), axis=0)
diffs = [float(np.nanmax(np.abs(circ31_ref(thr_raw_pipe, d) - thr_s_pipe[d-1]))) for d in range(153, 245)]
print("smoothing check max diff over target doys:", max(diffs))
print("INDEPENDENT VERIFICATION DONE")
