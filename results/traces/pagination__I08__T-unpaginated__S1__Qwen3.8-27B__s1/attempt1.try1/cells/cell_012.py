import numpy as np, datetime

thr_s = np.load('work/thr_s.npy')
sea = np.load('work/sea.npy')

# --- verify smoothing on one sea cell: recompute raw day-60-adjacent logic check ---
# rebuild raw thr from scratch quickly? Instead verify wraparound convolution property:
# smooth at index i must equal mean of raw[(i-15..i+15) mod 366]. We don't have raw here;
# but we can check consistency of thr_s with itself: not needed. Do a synthetic check of the routine instead.
def smooth31(raw):
    out = np.zeros_like(raw)
    for k in range(-15, 16):
        out += np.roll(raw, -k, axis=0)
    out /= 31.0
    return out
rng = np.random.default_rng(0)
raw = rng.random(366)
s = smooth31(raw)
i = 0
manual = raw[np.mod(np.arange(-15,16), 366)].mean()
print("smoothing check i=0:", np.abs(s[0]-manual) < 1e-12)
i = 100
manual = raw[np.mod(np.arange(100-15,100+16), 366)].mean()
print("smoothing check i=100:", np.abs(s[100]-manual) < 1e-12)

# --- verify hazen quantile semantics on a small sample ---
a = np.arange(1, 122, dtype=float)  # 1..121
q = np.quantile(a, 0.9, method='hazen')
# hazen: h = (n+1)*p = 122*0.9 = 109.8 -> between 109th and 110th order stats (109, 110)
print("hazen quantile:", q, "expected:", 109 + 0.8*(110-109))

# --- check day-60 fill happened: thr_s finite everywhere for sea cells? ---
print("NaNs in thr_s (sea cells):", int(np.isnan(thr_s[:, sea.ravel()]).sum()))

# --- basic magnitudes ---
ci, cj = 30, 30
col = sea[:, cj]
isr = np.where(col)[0]
print("cell lat idx range sample:", isr[:3], isr[-3:])
doy_target = np.load('work/tday_doy.npy')
print("thresholds at cell (30,30) for target DOYs (K):", np.round(thr_s[doy_target-1, 30*60+30][:5], 3), "...")
Xt = np.load('work/part_t1.npy')
print("SST at cell (30,30) first 5 target days (K):", Xt[:5, 30, 30])
mask = np.load('work/mask.npy')
print("mask totals: ones:", int(mask.sum()), "of", mask.size)
