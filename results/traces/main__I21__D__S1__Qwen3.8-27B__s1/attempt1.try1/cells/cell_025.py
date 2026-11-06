import numpy as np
z = np.load('/work/doy_stats.npz')
rt, rc = z['raw_thresh'], z['raw_clim']

def smooth366(a):
    # ext[i] = a[(i-15) mod 366]; window for day j (0-based) = ext[j .. j+30]
    ext = np.concatenate([a[-15:], a, a[:15]], axis=0)
    c2 = np.concatenate([np.zeros((1,) + a.shape[1:]), np.cumsum(ext, axis=0)], axis=0)
    lo = np.arange(len(a))
    return (c2[lo+31] - c2[lo]) / 31.0

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
rng = np.random.default_rng(0)
cols = rng.choice(sea, 5, replace=False)
ok = True
for col in cols:
    for d in [10, 100, 200, 366]:
        idx = [(d-16+i) % 366 for i in range(31)]
        if not (np.isclose(st[d-1,col], rt[idx, col].mean()) and np.isclose(sc[d-1,col], rc[idx, col].mean())):
            ok = False
print("random cell/window check:", ok)
np.savez_compressed('/work/doy_stats.npz', raw_thresh=rt, raw_clim=rc,
                    sm_thresh=st, sm_clim=sc, target_doy=z['target_doy'])
print("saved. sm finite frac:", np.isfinite(st).mean())
