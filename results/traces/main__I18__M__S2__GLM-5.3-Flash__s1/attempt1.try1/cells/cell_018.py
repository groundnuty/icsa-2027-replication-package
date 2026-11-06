import numpy as np

# --- numpy 'hazen' formula check: is it Hyndman-Fan type 5 (h_1based = n*p + 0.5)? ---
x = np.arange(1, 11, dtype=float)  # n=10
p = 0.9
q_np = np.percentile(x, 90, method="hazen")
h1 = 10*0.9 + 0.5      # 9.5 -> 0-based 8.5 -> mean(x[8],x[9])
manual = 0.5*(x[8]+x[9])
print("n=10 p=0.9: numpy hazen:", q_np, " manual type5:", manual, q_np == manual)
# also 'linear' (type 7) for contrast
print("numpy linear:", np.percentile(x, 90), " type7:", x[8] + 0.1*(x[9]-x[8]))

# --- redo check 1 (smoothing): correct manual indices ---
thr_raw = np.load("/tmp/thr_raw.npy"); thr = np.load("/tmp/thr.npy")
# smoothed doy 150 = idx 149 = mean raw idx 134..164 (doys 135..165)
manual149 = thr_raw[134:165, 30, 30].mean()
print("thr[149] vs mean raw idx134..164:", thr[149,30,30], manual149, abs(thr[149,30,30]-manual149) < 1e-9)
# smoothed doy 151 = idx 150
manual150 = thr_raw[135:166, 30, 30].mean()
print("thr[150] vs mean raw idx135..165:", thr[150,30,30], manual150, abs(thr[150,30,30]-manual150) < 1e-9)

# --- redo check 3 (day-60 rule) with equal_nan ---
print("raw day60 == mean(raw59,raw61):", np.allclose(thr_raw[59], 0.5*(thr_raw[58]+thr_raw[60]), equal_nan=True))
clim_raw = np.load("/tmp/clim_raw.npy")
print("clim raw day60 == mean:", np.allclose(clim_raw[59], 0.5*(clim_raw[58]+clim_raw[60]), equal_nan=True))
