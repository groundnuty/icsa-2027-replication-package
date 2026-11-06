import numpy as np, pickle
with open("/tmp/pool2.pkl","rb") as f: P = pickle.load(f)
pool, dates = P["pool"], P["dates"]
vals = np.load("/tmp/vals.npy")
with open("/tmp/clim.pkl","rb") as f: C = pickle.load(f)
THS, CLS, tdoy = C["THS"], C["CLS"], C["tdoy"]
hot = np.load("/tmp/hot.npy"); mask = np.load("/tmp/mask_lit.npy"); fin = np.load("/tmp/fin_all.npy")

# --- manual pool check: cell 0 (lat=59.06, lon=21.26), doy 180 (Jun 29 leap-cal) ---
d = 180
bdates = dates[(dates.astype('datetime64[Y]').astype(int)+1970 >= 1992) & (dates.astype('datetime64[Y]').astype(int)+1970 <= 2002) & (pool[d])]
print("doy 180 baseline anchor count:", bdates.size, bdates[0], bdates[-1])
win = np.zeros(vals.shape[0], bool)
for b in bdates:
    win |= np.abs((dates-b).astype(int)) <= 5
v = vals[win, 0]
print("pool size cell0 doy180:", v.size, "expected 121:", v.size == 121)
p90 = np.percentile(v, 90, method="hazen"); mn = v.mean()
print("manual raw TH %.6f vs pipeline %.6f | manual raw CL %.6f vs %.6f" % (p90, THS[179,0], mn, CLS[179,0]))

# brute-force smoothing check for cell 0, several doys, using raw TH/CL recomputed from pools
# recompute raw TH/CL for cell 0 only
TH0 = np.full(366, np.nan); CL0 = np.full(366, np.nan)
for dd in range(1,367):
    if dd == 60: continue
    v0 = vals[pool[dd], 0]
    TH0[dd-1] = np.percentile(v0, 90, method="hazen"); CL0[dd-1] = v0.mean()
TH0[59] = 0.5*(TH0[58]+TH0[60]); CL0[59] = 0.5*(CL0[58]+CL0[60])
mx = 0.0
for dd in [1, 2, 30, 60, 61, 180, 244, 365, 366]:
    idxs = [(dd-1+k) % 366 for k in range(-15, 16)]
    b = np.mean(TH0[idxs]); c = np.mean(CL0[idxs])
    mx = max(mx, abs(b-THS[dd-1,0]), abs(c-CLS[dd-1,0]))
print("brute-force circular smoothing max|diff| over sample doys:", mx)

# --- event 1 detail: which cells, daily mask counts ---
t0 = np.datetime64('2005-06-01')
for i in range(16, 24):
    print(t0+np.timedelta64(i,'D'), "active cells:", int(mask[i].sum()), "hot cells:", int(hot[i].sum()))
# the cell(s) in event 1
cols = np.where(mask[17:22].any(axis=0))[0]
print("cells in MHW during event1:", cols.size)
for c in cols:
    print("  cell", c, "hot:", hot[17:22, c].astype(int), "mask:", mask[17:22, c].astype(int))
