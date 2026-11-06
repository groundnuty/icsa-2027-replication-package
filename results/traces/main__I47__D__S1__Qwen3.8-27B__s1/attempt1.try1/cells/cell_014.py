import numpy as np, datetime as dt
data = np.load('/work/S.npz', allow_pickle=True)
S_base = data['S_base']
dates = [dt.date.fromisoformat(s) for s in data['dates']]
sea = np.isfinite(np.zeros((1,1))).all  # placeholder
S_tgt = data['S_tgt']
sea = np.isfinite(S_tgt).all(axis=0)
Sb = S_base[:, sea].astype(np.float64)
pools = np.load('/work/pools.npy', allow_pickle=True).item()

c = 2816; d = 234
vals = Sb[pools[d], c]
v = vals[~np.isnan(vals)]
print("n valid:", len(v), "of", len(vals))
sv_all = np.sort(vals)   # includes NaN at end
print("np.quantile hazen:", np.quantile(v, 0.9, method='hazen'))
n = len(v)
p = (n-1)*0.9
print("p:", p, "lo:", int(np.floor(p)), "frac:", p-np.floor(p))
vs = np.sort(v)
lo = int(np.floor(p)); frac = p - lo
mine = (1-frac)*vs[lo] + frac*vs[lo+1]
print("manual from valid-sorted:", mine)
# compare sv_all vs v-sorted alignment
print("sv_all[lo], sv_all[lo+1]:", sv_all[lo], sv_all[lo+1])
print("vs[lo], vs[lo+1]:", vs[lo], vs[lo+1])
print("first nan in sv_all:", np.isnan(sv_all).argmax() if np.isnan(sv_all).any() else None)
# check duplicates?
print("unique count in v:", len(np.unique(v)), "n:", n)
