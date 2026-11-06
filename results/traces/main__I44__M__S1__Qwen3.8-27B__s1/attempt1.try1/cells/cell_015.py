import numpy as np, datetime as dt, pickle

tgt3 = np.load("output/tgt_sst.npy").astype(np.float64)
mask = np.load("output/mask.npy")
thr = np.load("output/thr_smooth.npy")
thr_raw = np.load("output/thr_raw.npy")
tgt_days = pickle.load(open("output/tgt_days.pkl","rb"))
T = tgt3.shape[0]
tgt = tgt3.reshape(T, 3600)
y0 = dt.date(2004,1,1)
doy_t = np.array([(dt.date.fromisoformat(s) - y0).days + 1 for s in tgt_days])
lat_full = np.load("output/lat.npy"); lon_full = np.load("output/lon.npy")
lat_idx = np.load("output/lat_idx.npy"); lon_idx = np.load("output/lon_idx.npy")

c = 2074
li, lj = divmod(c, 60)
print("cell region lat/lon:", lat_full[lat_idx[li]], lon_full[lon_idx[lj]])
for i in range(T):
    sst = tgt[i, c]
    th = thr[doy_t[i]-1, c]
    flag = "M" if mask[i, c] else ("H" if (np.isfinite(sst) and sst >= th) else ".")
    if flag != ".":
        print(tgt_days[i], "doy=%3d" % doy_t[i], "SST=%.2f thr=%.2f %s" % (sst, th, flag))

# verify hazen == HF type 5: k = n*p + 0.5
bas = np.load("output/bas_sst.npy").astype(np.float64)
bas_days = pickle.load(open("output/bas_days.pkl","rb"))
b0 = min(dt.date.fromisoformat(s).toordinal() for s in bas_days)
d = 183
idx = np.array(sorted(set(o+k for y in range(1992,2003) for o in [(dt.date(y,1,1)+dt.timedelta(days=d-1)).toordinal()] for k in range(-5,6))))
vals_c = np.sort(bas[idx - b0, li, lj]); vals_c = vals_c[np.isfinite(vals_c)]
n = vals_c.size
q_np = np.quantile(vals_c, 0.9, method="hazen")
k = n*0.9 + 0.5
q_t5 = vals_c[int(np.floor(k))-1] + (k - np.floor(k))*(vals_c[int(np.ceil(k))-1] - vals_c[int(np.floor(k))-1])
print("\nhazen(numpy): %.9f | HF-type5 k=np+0.5: %.9f | match: %s" % (q_np, q_t5, abs(q_np-q_t5) < 1e-9))
# also compare with type 7 (linear / MATLAB-style) to show they differ
q_t7 = np.quantile(vals_c, 0.9, method="linear")
print("type7(linear): %.9f (differs as expected: %.6f)" % (q_t7, q_t7 - q_np))
