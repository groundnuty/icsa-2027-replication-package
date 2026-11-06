import numpy as np, pickle
D = pickle.load(open("/tmp/mhw_data.pkl","rb"))
M = pickle.load(open("/tmp/mhw_masks.pkl","rb"))
B, T = D["B"], D["T"]
masks = M["masks"]; nb = B.shape[0]
sea = np.all(np.isfinite(T), axis=0)
cells = np.argwhere(sea); n_sea = cells.shape[0]
V = B[:, cells[:,0], cells[:,1]].T
assert V.shape == (n_sea, nb) and np.isfinite(V).all()

def hazen90(P):
    Xs = np.sort(P, axis=1); c = P.shape[1]
    h0 = 0.9*(c-1); j = int(np.floor(h0)); g = h0-j
    return Xs[:,j] + (g*(Xs[:,j+1]-Xs[:,j]) if g>0 else 0.0)

Th = np.empty((n_sea,366)); Cl = np.empty((n_sea,366))
for d in range(1,367):
    if d == 60: continue
    P = V[:, masks[d]]
    Th[:,d-1] = hazen90(P); Cl[:,d-1] = P.mean(axis=1)
Th[:,59] = (Th[:,58]+Th[:,60])/2.0; Cl[:,59] = (Cl[:,58]+Cl[:,60])/2.0
assert np.isfinite(Th).all() and np.isfinite(Cl).all()

# cross-check vs numpy hazen on random cells/doys
rng = np.random.default_rng(0)
cs = rng.integers(0, n_sea, 20); ds = rng.integers(1, 366, 20); ds[ds==60]=61
diff = max(abs(np.quantile(V[c, masks[d]], 0.90, method="hazen") - Th[c, d-1]) for c,d in zip(cs,ds))
mdiff = max(abs(V[c, masks[d]].mean() - Cl[c, d-1]) for c,d in zip(cs,ds))
print("max abs diff vs numpy hazen: %.3e ; clim: %.3e" % (diff, mdiff))
print("Th range: %.3f .. %.3f K ; Cl range: %.3f .. %.3f K" % (Th.min(),Th.max(),Cl.min(),Cl.max()))
pickle.dump({"Th":Th,"Cl":Cl,"cells":cells,"sea":sea,"n_sea":n_sea}, open("/tmp/mhw_thresh.pkl","wb"))
print("saved")