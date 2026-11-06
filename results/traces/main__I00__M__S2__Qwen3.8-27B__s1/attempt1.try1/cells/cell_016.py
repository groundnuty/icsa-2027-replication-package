import numpy as np, datetime as dt
S = np.load("/tmp/S.npy")
sea = np.load("/tmp/sea.npy")
doy = np.load("/tmp/doy.npy")
base = dt.date(1991,12,27)

# pool for doy 190 (Jul 9): windows Jul 4-14 of each year 1992..2002
idx = []
for y in range(1992, 2003):
    b = (dt.date(y,7,9) - base).days
    idx += [b+off for off in range(-5,6)]
idx = np.array(sorted(set(idx)))
print("n pool:", len(idx), "first/last:", base+dt.timedelta(days=idx[0]), base+dt.timedelta(days=idx[-1]))
vals = S[sea][10, idx]
srt = np.sort(vals)
print("pool min/max:", vals.min(), vals.max(), "mean:", vals.mean())
print("sorted tail (last 15):", srt[-15:].round(3))
print("hazen q90:", np.quantile(vals, 0.9, method='hazen'))
print("linear q90:", np.quantile(vals, 0.9, method='linear'))
# how do the window days look across years for this cell (July 9 each year)?
for y in range(1992,2003):
    k = (dt.date(y,7,9) - base).days
    print(y, "Jul9 SST:", round(float(S[sea][10, k]),2))
