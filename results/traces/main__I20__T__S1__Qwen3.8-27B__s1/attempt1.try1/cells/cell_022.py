import numpy as np, pickle, datetime as dt

D = pickle.load(open("/tmp/mhw_data.pkl","rb"))
B, T = D["B"], D["T"]
nb, nlat, nlon = B.shape
masks = pickle.load(open("/tmp/mhw_masks.pkl","rb"))["masks"]

sea = np.all(np.isfinite(T), axis=0)
cells = np.argwhere(sea); n_sea = cells.shape[0]
V = B[:, cells[:,0], cells[:,1]].T   # (n_sea, 4071), all finite
assert np.isfinite(V).all()

def quantile_all(P, method):
    """P: (n_cells, m) finite. Return quantile 0.9 per row per method formula."""
    Xs = np.sort(P, axis=1)
    n = P.shape[1]
    if method == "hazen":   # numpy 2.x 'hazen': 0-based virtual = n*p - 0.5
        h0 = n*0.9 - 0.5
    else:                   # 'linear' = MATLAB default = (n-1)p
        h0 = (n-1)*0.9
    j = int(np.floor(h0)); g = h0 - j
    if g == 0:
        return Xs[:, j]
    return Xs[:, j] + g*(Xs[:, j+1] - Xs[:, j])

def smooth31(A):
    """A: (n,366) -> periodic centred 31-day moving mean."""
    idx = np.array([[(d-15+k) % 366 for k in range(31)] for d in range(366)])
    return A.take(idx, axis=1).mean(axis=1)

def pipeline(method):
    Th = np.empty((n_sea,366)); Cl = np.empty((n_sea,366))
    for d in range(1,367):
        if d == 60: continue
        P = V[:, masks[d]]
        Th[:,d-1] = quantile_all(P, method)
        Cl[:,d-1] = P.mean(axis=1)
    Th[:,59] = (Th[:,58]+Th[:,60])/2.0
    Cl[:,59] = (Cl[:,58]+Cl[:,60])/2.0
    Ths = smooth31(Th); Cls = smooth31(Cl)
    # hot days
    tdays = D["tgt_dates"]
    tdoys = np.array([month_start(d.month-1)+d.day for d in tdays])
    msk = np.zeros((92, nlat, nlon), dtype=np.uint8)
    # per cell
    for ci, (i, j) in enumerate(cells):
        h = np.zeros(92, dtype=bool)
        h[:] = T[:, i, j] >= Ths[ci, tdoys-1]
        # runs >=5
        runs = []
        k = 0
        while k < 92:
            if h[k]:
                l = k
                while l+1 < 92 and h[l+1]: l += 1
                if l-k+1 >= 5: runs.append([k, l])
                k = l+1
            else:
                k += 1
        merged = []
        for s, e in runs:
            if merged and s - merged[-1][1] - 1 <= 2:
                merged[-1][1] = e
            else:
                merged.append([s, e])
        for s, e in merged:
            msk[s:e+1, i, j] = 1
    active = (msk.sum(axis=(1,2)) > 0)
    evs = []
    k = 0
    while k < 92:
        if active[k]:
            l = k
            while l+1 < 92 and active[l+1]: l += 1
            evs.append((str(tdays[k]), str(tdays[l])))
            k = l+1
        else:
            k += 1
    return Ths, Cls, msk, evs, tdoys

mlen = [31,29,31,30,31,30,31,31,30,31,30,31]
month_start = [0]
for m in mlen: month_start.append(month_start[-1]+m)

res_h = pipeline("hazen")
res_l = pipeline("linear")
msk_h, evs_h = res_h[2], res_h[3]
msk_l, evs_l = res_l[2], res_l[3]
print("hazen events:", evs_h)
print("linear events:", evs_l)
print("mask equal:", bool((msk_h==msk_l).all()))
diff = (msk_h!=msk_l)
print("mask diff cells*days:", int(diff.sum()))
print("total mhw days (hazen):", int(msk_h.sum()), "active days:", int((msk_h.sum(axis=(1,2))>0).sum()))
pickle.dump({"Ths_h":res_h[0],"Cl_h":res_h[1],"Ths_l":res_l[0],"Cl_l":res_l[1],
             "msk_h":msk_h,"msk_l":msk_l,"evs_h":evs_h,"evs_l":evs_l},
            open("/tmp/mhw_results.pkl","wb"))
print("saved")