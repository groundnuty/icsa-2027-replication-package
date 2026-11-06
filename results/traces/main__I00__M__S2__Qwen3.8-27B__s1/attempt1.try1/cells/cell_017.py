import numpy as np, datetime as dt
S = np.load("/tmp/S.npy")
sea = np.load("/tmp/sea.npy")
base = dt.date(1991,12,27)

idx = []
for y in range(1992, 2003):
    b = (dt.date(y,7,9) - base).days
    idx += [b+off for off in range(-5,6)]
idx = np.array(sorted(set(idx)), dtype=int)
print("n pool:", len(idx), "first/last:", base+dt.timedelta(days=int(idx[0])), base+dt.timedelta(days=int(idx[-1])))
vals = S[sea][10, idx]
srt = np.sort(vals)
print("pool min/max: %.2f %.2f mean %.2f" % (vals.min(), vals.max(), vals.mean()))
print("sorted tail (last 15):", srt[-15:].round(3))
print("hazen q90: %.3f" % np.quantile(vals, 0.9, method='hazen'))
print("linear q90: %.3f" % np.quantile(vals, 0.9, method='linear'))
for y in range(1992,2003):
    k = (dt.date(y,7,9) - base).days
    print(y, "Jul9 SST: %.2f" % S[sea][10, k])
