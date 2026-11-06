import numpy as np, pickle
D = pickle.load(open("/tmp/mhw_data.pkl","rb"))
R = pickle.load(open("/tmp/mhw_results.pkl","rb"))
B, T = D["B"], D["T"]
Ths = R["Ths_h"]; tdoys = R["tdoys"]
sea = np.all(np.isfinite(T), axis=0)
cells = np.argwhere(sea)

# threshold stats over target doys
print("Ths target-doy range: %.3f .. %.3f K" % (Ths[:, tdoys-1].min(), Ths[:, tdoys-1].max()))
print("T range: %.3f .. %.3f K, finite frac %.3f" % (np.nanmin(T), np.nanmax(T), np.isfinite(T).mean()))

# per cell: number of hot days
hotcnt = np.zeros(len(cells), int)
for ci,(i,j) in enumerate(cells):
    hotcnt[ci] = np.sum(T[:,i,j] >= Ths[ci, tdoys-1])
print("hot days per cell: min %d max %d mean %.2f, cells with any hot: %d" %
      (hotcnt.min(), hotcnt.max(), hotcnt.mean(), (hotcnt>0).sum()))
# look at one cell in detail
ci = 1500
i,j = cells[ci]
th = Ths[ci, tdoys-1]
t = T[:,i,j]
print("cell", i, j, "sst min/max %.2f/%.2f th min/max %.2f/%.2f" % (np.nanmin(t), np.nanmax(t), th.min(), th.max()))
print("diff (sst-th) max:", np.nanmax(t-th), " mean:", np.nanmean(t-th))
# is this cell near coast? check land neighbors in baseline
print("baseline finite frac for cell:", np.isfinite(B[:,i,j]).mean())
# maybe threshold is systematically high? check one pool manually
masks = pickle.load(open("/tmp/mhw_masks.pkl","rb"))["masks"]
d = 170
P = B[masks[d], i, j]
print("doy170 pool: n=%d min=%.2f max=%.2f mean=%.2f p90hazen~" % (len(P), P.min(), P.max(), P.mean()),
      np.quantile(P, 0.9, method="hazen"))
print("2012 sst at doy170 (2012-06-18):", T[17, i, j])