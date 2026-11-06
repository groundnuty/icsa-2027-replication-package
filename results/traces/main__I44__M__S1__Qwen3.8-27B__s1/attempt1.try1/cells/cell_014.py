import numpy as np, datetime as dt, pickle

tgt3 = np.load("output/tgt_sst.npy").astype(np.float64)
mask = np.load("output/mask.npy")
thr = np.load("output/thr_smooth.npy")
tgt_days = pickle.load(open("output/tgt_days.pkl","rb"))
T = tgt3.shape[0]
tgt = tgt3.reshape(T, 3600)
y0 = dt.date(2004,1,1)
doy_t = np.array([(dt.date.fromisoformat(s) - y0).days + 1 for s in tgt_days])

# 1) active days and boundary check
active = mask.any(axis=1)
for i, s in enumerate(tgt_days):
    if active[i]:
        print(s, "active, n cells:", int(mask[i].sum()))
print("day before:", tgt_days[[i for i in range(T) if active[i]][0]-1], "active?", bool(active[[i for i in range(T) if active[i]][0]-1]))
print("day after:", tgt_days[[i for i in range(T) if active[i]][-1]+1], "active?", bool(active[[i for i in range(T) if active[i]][-1]+1]))

# 2) pick one event cell, inspect its hot pattern vs threshold
c = int(np.flatnonzero(mask.any(axis=0))[0])
print("\ncell", c, "lat idx/lon idx:", divmod(c, 60))
lat = np.load("output/lat.npy"); lon = np.load("output/lon.npy")
li, lj = np.unravel_index(c, (60, 60))
print("lat,lon:", lat[li], lon[lj])
seq = "".join("#" if mask[i, c] else ("." if not np.isfinite(tgt[i, c]) else "-") for i in range(T))
hotseq = "".join("H" if (np.isfinite(tgt[i, c]) and tgt[i, c] >= thr[doy_t[i]-1, c]) else " " for i in range(T))
print("mask : ", seq)
print("hot  : ", hotseq)
print("dates:", " ".join(s[5:] for s in tgt_days))
vals = [("%.2f/%.2f" % (tgt[i, c], thr[doy_t[i]-1, c])) for i in range(T-8, T)]
print("SST/thr last 8 days:", vals)

# 3) verify hazen quantile independently on one pool (doy=183, this cell)
bas = np.load("output/bas_sst.npy").astype(np.float64)
bas_days = pickle.load(open("output/bas_days.pkl","rb"))
b_ord = {s: dt.date.fromisoformat(s).toordinal() for s in bas_days}
b0 = min(b_ord.values())
def isleap(y): return (y % 4 == 0) and (y % 100 != 0 or y % 400 == 0)
d = 183
idx_set = set()
for y in range(1992, 2003):
    o = (dt.date(y,1,1) + dt.timedelta(days=d-1)).toordinal()
    idx_set |= set(range(o-5, o+6))
idx = np.array(sorted(idx_set))
vals_c = bas[idx - b0, li, lj]
vals_c = vals_c[np.isfinite(vals_c)]
print("\npool n finite:", vals_c.size, "of", len(idx))
q_np = np.quantile(vals_c, 0.9, method="hazen")
# manual hazen: h = (n-1)*0.9 + 1 (1-based)
n = vals_c.size
h = (n - 1) * 0.9 + 1
lo = np.floor(h); hi = np.ceil(h)
x = np.sort(vals_c)
q_man = x[lo-1] + (h - lo) * (x[hi-1] - x[lo-1]) if hi > lo else x[int(h)-1]
print("hazen via numpy: %.6f | manual: %.6f" % (q_np, q_man))
print("raw pool mean: %.6f" % vals_c.mean())
print("raw thr[183] this cell: %.6f (should equal q_np)" % np.load("output/thr_raw.npy")[182, c])
