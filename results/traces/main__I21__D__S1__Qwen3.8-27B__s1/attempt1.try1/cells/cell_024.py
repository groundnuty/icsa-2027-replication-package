import numpy as np
z = np.load('/work/doy_stats.npz')
rt, rc = z['raw_thresh'], z['raw_clim']

def smooth366(a):
    ext = np.concatenate([a[-15:], a, a[:15]], axis=0)
    c = np.cumsum(ext, axis=0)
    lo = np.arange(len(a)); hi = lo + 31
    return (c[hi] - c[lo]) / 31.0

st = smooth366(rt); sc = smooth366(rc)
finite_all = np.all(np.isfinite(rt), axis=0)
sea = np.where(finite_all)[0]
print("sm thr sea range:", st[:, sea].min(), st[:, sea].max())
print("sm clim sea range:", sc[:, sea].min(), sc[:, sea].max())
col = sea[0]
for d in [1, 60, 153, 244, 366]:
    idx = [(d-16+i) % 366 for i in range(31)]
    mt = rt[idx, col].mean(); mc = rc[idx, col].mean()
    print("d=", d, "thr diff:", abs(st[d-1,col]-mt), "clim diff:", abs(sc[d-1,col]-mc))
# also verify against a direct per-element loop for a few random sea cells
rng = np.random.default_rng(0)
cols = rng.choice(sea, 5, replace=False)
ok = True
for col in cols:
    for d in [10, 100, 200, 366]:
        idx = [(d-16+i) % 366 for i in range(31)]
        if not np.allclose(st[d-1,col], rt[idx, col].mean()): ok = False
print("random cell/window check:", ok)
np.savez_compressed('/work/doy_stats.npz', raw_thresh=rt, raw_clim=rc,
                    sm_thresh=st, sm_clim=sc, target_doy=z['target_doy'])
print("saved. sm finite frac:", np.isfinite(st).mean())
