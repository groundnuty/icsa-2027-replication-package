import numpy as np, pickle

D = pickle.load(open("/tmp/mhw_data.pkl","rb"))
M = pickle.load(open("/tmp/mhw_masks.pkl","rb"))
B, T = D["B"], D["T"]
masks = M["masks"]
nb, nlat, nlon = B.shape

sea = np.all(np.isfinite(T), axis=0)
cells = np.argwhere(sea)
n_sea = cells.shape[0]
V = B[:, cells[:,0], cells[:,1]].T      # (n_sea, 4071)
assert V.shape == (n_sea, nb)
assert np.isfinite(V).all()

def hazen90(P):
    Xs = np.sort(P, axis=1)
    c = P.shape[1]
    h0 = 0.9*(c-1)
    j = int(np.floor(h0)); g = h0 - j
    if g == 0:
        return Xs[:, j]
    return Xs[:, j] + g*(Xs[:, j+1] - Xs[:, j])

Th = np.empty((n_sea, 366)); Cl = np.empty((n_sea, 366))
for d in range(1, 367):
    if d == 60: continue
    P = V[:, masks[d]]
    Th[:, d-1] = hazen90(P)
    Cl[:, d-1] = P.mean(axis=1)
Th[:, 59] = (Th[:, 58] + Th[:, 60]) / 2.0
Cl[:, 59] = (Cl[:, 58] + Cl[:, 60]) / 2.0
assert np.isfinite(Th).all() and np.isfinite(Cl).all()
print("Th range: %.2f .. %.2f K ; Cl range: %.2f .. %.2f K" % (Th.min(), Th.max(), Cl.min(), Cl.max()))

# manual cross-check
d = 153
Pman = V[0, masks[d]]
x = np.sort(Pman); n = len(x)
h0 = 0.9*(n-1); j = int(np.floor(h0)); g = h0-j
qman = x[j] + (g*(x[j+1]-x[j]) if g>0 else 0.0)
print("verify cell0 doy153: manual %.9f vs %.9f (n=%d)" % (qman, Th[0,152], n))
print("clim manual %.9f vs %.9f" % (Pman.mean(), Cl[0,152]))
# second check: doy 59/61 -> 60
print("day60 check: (Th59+Th61)/2 = %.9f vs stored %.9f (cell 0)" % ((Th[0,58]+Th[0,60])/2, Th[0,59]))

# numpy hazen cross-check for a few cells/doys
chk = np.array([np.quantile(V[c, masks[200]], 0.90, method="hazen") for c in range(0, n_sea, 997)])
mine = Th[[0,997,1994,2991,3313], 199]
print("numpy hazen cross-check max diff:", float(np.max(np.abs(chk - mine))))

pickle.dump({"Th":Th,"Cl":Cl,"cells":cells,"sea":sea,"n_sea":n_sea}, open("/tmp/mhw_thresh.pkl","wb"))
print("saved")