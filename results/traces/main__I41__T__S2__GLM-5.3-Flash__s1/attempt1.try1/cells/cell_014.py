import numpy as np, datetime as dt

thr_raw = np.load('work/thr_raw.npy'); clim_raw = np.load('work/clim_raw.npy')
T = np.load('work/T.npy').astype(np.float64)   # (92, 60, 60) float64

def smooth31(a):
    """a: (366, ...) -> centred 31-day moving mean, wrapping mod 366 (unweighted)."""
    n = a.shape[0]
    assert n == 366
    pad = np.concatenate([a[-15:], a, a[:15]], axis=0)   # length 366+30
    csum = np.concatenate([np.zeros((1,)+a.shape[1:]), np.cumsum(pad, axis=0)], axis=0)
    return (csum[31:] - csum[:-31]) / 31.0               # window [i, i+31) -> centres i+15

thr_s = smooth31(thr_raw)
clim_s = smooth31(clim_raw)
print("thr_s shape:", thr_s.shape, "| finite frac:", np.isfinite(thr_s).mean(), "| clim_s finite frac:", np.isfinite(clim_s).mean())

# spot-check smoothing by brute force on one cell, one doy
cell = (30,30)
d = 153  # doy 153 -> index 152
idxs = [(152 + k) % 366 for k in range(-15, 16)]
brute = np.mean(thr_raw[idxs, cell[0], cell[1]])
print("smoothing check doy153 cell(30,30): brute", brute, "vs smooth", thr_s[152][cell], "| match:", np.isclose(brute, thr_s[152][cell]))
d = 1  # doy 1 -> index 0
idxs = [(0 + k) % 366 for k in range(-15, 16)]
brute = np.mean(thr_raw[idxs, cell[0], cell[1]])
print("smoothing check doy1 (wrap): brute", brute, "vs smooth", thr_s[0][cell], "| match:", np.isclose(brute, thr_s[0][cell]))
d = 366
idxs = [(365 + k) % 366 for k in range(-15, 16)]
brute = np.mean(thr_raw[idxs, cell[0], cell[1]])
print("smoothing check doy366 (wrap): brute", brute, "vs smooth", thr_s[365][cell], "| match:", np.isclose(brute, thr_s[365][cell]))

# ---- per-cell hot days over target period ----
def leap(y): return y%4==0 and (y%100!=0 or y%400==0)
def doy_of(d):
    n = (d - dt.date(d.year,1,1)).days + 1
    if d.month >= 3 and not leap(d.year): n += 1
    return n

tdates = [dt.date(2021,6,1)+dt.timedelta(days=i) for i in range(92)]
tdoy = np.array([doy_of(d) for d in tdates])  # 153..244 (2021 non-leap)
print("target doys:", tdoy.min(), "..", tdoy.max(), "| n:", len(tdoy))
assert tdoy.min()==153 and tdoy.max()==244

# hot: SST (float64) >= threshold for that doy; NaN -> False
thr_t = thr_s[tdoy-1]          # (92, 60, 60)
hot = T >= thr_t
hot &= np.isfinite(T)
print("hot day-fraction over target:", hot.mean())
np.save('work/thr_s.npy', thr_s); np.save('work/clim_s.npy', clim_s); np.save('work/hot.npy', hot)
print("saved smoothed arrays and hot mask.")
