import numpy as np, pickle
D = pickle.load(open("/tmp/mhw_data.pkl","rb"))
M = pickle.load(open("/tmp/mhw_masks.pkl","rb"))
B, T = D["B"], D["T"]; masks = M["masks"]; nb = B.shape[0]
sea = np.all(np.isfinite(T), axis=0)
cells = np.argwhere(sea); n_sea = cells.shape[0]
V = B[:, cells[:,0], cells[:,1]].T
Th = pickle.load(open("/tmp/mhw_thresh.pkl","rb"))["Th"]

rng = np.random.default_rng(0)
cs = rng.integers(0, n_sea, 20); ds = rng.integers(1, 366, 20); ds[ds==60]=61
for c,d in zip(cs,ds):
    P = V[c, masks[d]]
    qn = np.quantile(P, 0.90, method="hazen")
    qm = Th[c, d-1]
    if abs(qn-qm) > 1e-9:
        print("MISMATCH c=%d d=%d numpy=%.9f mine=%.9f npool=%d" % (c,d,qn,qm,len(P)))
        x = np.sort(P)
        n = len(x)
        # recompute hazen by hand
        h0 = 0.9*(n-1); j=int(np.floor(h0)); g=h0-j
        qh = x[j]+(g*(x[j+1]-x[j]) if g>0 else 0.0)
        print("  hand=%.9f n=%d j=%d g=%.6f xj=%.9f xj1=%.9f" % (qh,n,j,g,x[j],x[j+1]))
        # check for duplicate values / ties
        u = np.unique(P)
        print("  unique pool values:", u[:5], "...", u[-5:], "n unique:", len(u))
        print("  P sorted around q:", x[100:112])
        break